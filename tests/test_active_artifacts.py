from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from impl.core.active_artifacts import (
    ActiveArtifactFamily,
    ActiveArtifactRegistry,
    DEFAULT_ACTIVE_ARTIFACT_REGISTRY,
)
from impl.core.path_contract import PathContractError


def test_registry_rejects_unknown_json_in_active_state_directory(tmp_path: Path) -> None:
    unknown = (
        tmp_path
        / "impl"
        / "projects"
        / "demo"
        / "draft"
        / ".state"
        / "attribute"
        / "unregistered.json"
    )
    unknown.parent.mkdir(parents=True)
    unknown.write_text("{}\n", encoding="utf-8")

    failures = DEFAULT_ACTIVE_ARTIFACT_REGISTRY.validate(tmp_path, environ={})

    assert len(failures) == 1
    assert failures[0].code == "PATH_ACTIVE_UNKNOWN"
    assert failures[0].path == unknown


def test_registry_treats_draft_loop_revision_history_as_historical(tmp_path: Path) -> None:
    history_file = (
        tmp_path
        / "impl"
        / "projects"
        / "demo"
        / "draft"
        / ".state"
        / "mock"
        / "history"
        / "001"
        / "iterations"
        / "001-run.json"
    )
    history_file.parent.mkdir(parents=True)
    history_file.write_text('{"run_status":"completed"}\n', encoding="utf-8")

    assert (
        DEFAULT_ACTIVE_ARTIFACT_REGISTRY.classify_path(tmp_path, history_file)
        == "historical"
    )
    failures = DEFAULT_ACTIVE_ARTIFACT_REGISTRY.validate(tmp_path, environ={})
    assert all(failure.path != history_file for failure in failures)


def test_registry_classifies_integrity_failures_without_mutating_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "impl" / "projects" / "demo" / "active.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"sha256": "old"}\n', encoding="utf-8")
    before = artifact.read_bytes()

    def stale(_context, _path) -> None:
        raise ValueError("content hash changed; expected=old, actual=new")

    registry = ActiveArtifactRegistry(
        (
            ActiveArtifactFamily(
                family_id="test_integrity",
                lifecycle="derived_active",
                pattern="*/active.json",
                validator=stale,
            ),
        )
    )

    failures = registry.validate(tmp_path, environ={})

    assert [(item.code, item.family_id) for item in failures] == [
        ("PATH_INTEGRITY_STALE", "test_integrity")
    ]
    assert artifact.read_bytes() == before


def test_registry_rejects_duplicate_family_ids() -> None:
    family = ActiveArtifactFamily("duplicate", "derived_active", "*.json", lambda *_: None)

    try:
        ActiveArtifactRegistry((family, family))
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate active artifact family id was accepted")


def test_registered_writer_requires_known_family_and_owned_target(tmp_path: Path) -> None:
    registry = ActiveArtifactRegistry(
        (
            ActiveArtifactFamily(
                family_id="demo_state",
                lifecycle="derived_active",
                pattern="*/state.json",
                validator=lambda *_: None,
                payload_validator=lambda _context, _path, payload: (
                    None
                    if isinstance(payload, dict) and payload.get("schema_version") == 1
                    else (_ for _ in ()).throw(ValueError("schema_version must be 1"))
                ),
            ),
        )
    )
    target = tmp_path / "impl" / "projects" / "demo" / "state.json"

    written = registry.write_json(
        "demo_state",
        target,
        {"schema_version": 1},
        root=tmp_path,
    )

    assert written == target
    with pytest.raises(PathContractError, match="PATH_ACTIVE_UNKNOWN"):
        registry.write_json(
            "missing",
            target,
            {"schema_version": 1},
            root=tmp_path,
        )
    with pytest.raises(PathContractError, match="PATH_ACTIVE_UNKNOWN"):
        registry.write_json(
            "demo_state",
            tmp_path / "outside.json",
            {"schema_version": 1},
            root=tmp_path,
        )


def test_registered_writer_validates_family_payload_before_write(tmp_path: Path) -> None:
    def require_version(_context, _path, payload) -> None:
        if not isinstance(payload, dict) or payload.get("schema_version") != 2:
            raise ValueError("schema_version must be 2")

    registry = ActiveArtifactRegistry(
        (
            ActiveArtifactFamily(
                "demo_state",
                "derived_active",
                "*/state.json",
                lambda *_: None,
                payload_validator=require_version,
            ),
        )
    )
    target = tmp_path / "impl" / "projects" / "demo" / "state.json"

    with pytest.raises(ValueError, match="schema_version must be 2"):
        registry.write_json(
            "demo_state",
            target,
            {"schema_version": 1},
            root=tmp_path,
        )

    assert not target.exists()


def test_registry_star_pattern_does_not_cross_directory_boundary(tmp_path: Path) -> None:
    nested = tmp_path / "impl" / "data" / "demo" / "nested" / "mock_cases.json"
    nested.parent.mkdir(parents=True)

    with pytest.raises(PathContractError, match="PATH_ACTIVE_UNKNOWN"):
        DEFAULT_ACTIVE_ARTIFACT_REGISTRY.write_json(
            "project_mock_cases",
            nested,
            [],
            root=tmp_path,
        )


def test_context_record_writer_and_scanner_share_registered_context(tmp_path: Path) -> None:
    repository_root = tmp_path / "verifier"
    config_path = repository_root / "impl" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    source_config = Path(__file__).resolve().parents[1] / "impl" / "config.yaml"
    shutil.copyfile(source_config, config_path)
    store_root = tmp_path / "machine-context-store"
    context = DEFAULT_ACTIVE_ARTIFACT_REGISTRY.context(
        repository_root,
        environ={"CONTEXT_STORE_ROOT": str(store_root)},
    )
    target = store_root / "demo" / "trace-1" / "attribute-record.json"
    payload = {
        "record_id": "record-1",
        "trace_id": "trace-1",
        "project_id": "demo",
        "caller": "attribute",
        "messages": [],
        "created_at": "2026-07-23T00:00:00Z",
    }

    DEFAULT_ACTIVE_ARTIFACT_REGISTRY.write_json(
        "context_record",
        target,
        payload,
        context=context,
    )

    assert DEFAULT_ACTIVE_ARTIFACT_REGISTRY.validate_context(context) == []
    with pytest.raises(PathContractError, match="PATH_ACTIVE_UNKNOWN"):
        DEFAULT_ACTIVE_ARTIFACT_REGISTRY.write_json(
            "context_record",
            tmp_path / "unregistered" / "demo" / "trace-1" / "record.json",
            payload,
            context=context,
        )


def test_solidify_probe_writer_uses_registered_family(tmp_path: Path) -> None:
    from impl.core.solidify import write_solidify_probe_result

    root = tmp_path / "verifier"
    target = (
        root
        / "impl"
        / "projects"
        / "demo"
        / "draft"
        / "probes"
        / "judge-solidify-smoke.json"
    )
    target.parent.mkdir(parents=True)
    payload = {
        "status": "succeeded",
        "project_id": "demo",
        "role": "judge",
        "observed_asset_ids": ["candidate_role"],
        "checks": {"candidate_instantiated": True},
    }

    written = write_solidify_probe_result(target, payload)

    assert written == target
    assert DEFAULT_ACTIVE_ARTIFACT_REGISTRY.validate(root, environ={}) == []

    invalid_target = target.with_name("mock-solidify-smoke.json")
    with pytest.raises(ValueError, match="identity mismatch"):
        write_solidify_probe_result(invalid_target, payload)
    assert not invalid_target.exists()


def test_role_review_registry_checks_only_latest_iteration_against_active_solidify(
    tmp_path: Path, monkeypatch
) -> None:
    import json

    from impl.core import draft_role_review
    from impl.core.active_artifacts import ActiveArtifactContext, _validate_draft_role_review
    from impl.core.path_contract import PathResolver, PathRoots
    from impl.core.portable_artifact import PortableArtifactWriter

    root = tmp_path / "verifier"
    project_root = root / "impl" / "projects" / "demo"
    iterations = project_root / "draft" / ".state" / "judge" / "iterations"
    iterations.mkdir(parents=True)
    roots = PathRoots(
        verifier_repo=root.resolve(),
        project_package=project_root.resolve(),
        knowledge_route=project_root.resolve(),
        artifact_package=project_root.resolve(),
    )

    class Spec:
        project_id = "demo"
        path_resolver = PathResolver(roots)

    context = ActiveArtifactContext(
        root=root,
        dotenv_path=root / ".env",
        environ={},
        writer=PortableArtifactWriter(),
    )
    monkeypatch.setattr(
        ActiveArtifactContext,
        "project_spec",
        lambda _self, project_id: Spec() if project_id == "demo" else None,
    )
    checks: list[tuple[int, bool]] = []

    def require_review(_spec, _role, iteration, **kwargs):
        checks.append((iteration, kwargs["check_current_solidify"]))
        return {}

    monkeypatch.setattr(draft_role_review, "require_draft_role_review", require_review)
    review_paths = []
    for iteration in (1, 2):
        run_report = iterations / f"{iteration:03d}-run.json"
        run_report.write_text("{}\n", encoding="utf-8")
        review_path = iterations / f"{iteration:03d}-role-review.json"
        review_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project_id": "demo",
                    "role": "judge",
                    "iteration": iteration,
                    "run_report": {
                        "location_scope": "project_package",
                        "location": (
                            "draft/.state/judge/iterations/"
                            f"{iteration:03d}-run.json"
                        ),
                    },
                    "decision": "unchanged",
                    "route": "solidify",
                }
            ),
            encoding="utf-8",
        )
        review_paths.append(review_path)

    for review_path in review_paths:
        _validate_draft_role_review(context, review_path)

    assert checks == [(1, False), (2, True)]



def _blocked_role_fixture(
    root: Path,
    *,
    role: str = "judge",
    status: str = "blocked",
    review_solidify_sha256: str = "",
) -> tuple[Path, Path, Path]:
    role_root = root / "impl" / "projects" / "demo" / "draft" / ".state" / role
    iterations = role_root / "iterations"
    iterations.mkdir(parents=True, exist_ok=True)
    run_report = iterations / "001-run.json"
    run_report.write_text("{}\n", encoding="utf-8")
    run_sha256 = hashlib.sha256(run_report.read_bytes()).hexdigest()
    review_path = iterations / "001-role-review.json"
    review_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_id": "demo",
                "role": role,
                "iteration": 1,
                "run_report": {
                    "location_scope": "project_package",
                    "location": f"draft/.state/{role}/iterations/001-run.json",
                    "sha256": run_sha256,
                },
                "run_report_sha256": run_sha256,
                "solidify_receipt_sha256": review_solidify_sha256,
                "decision": "blocked",
                "route": "blocked",
                "summary": "model gateway returned 403",
                "contract_coverage": [],
                "criteria": [],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    review_sha256 = hashlib.sha256(review_path.read_bytes()).hexdigest()
    loop_path = role_root / "loop.json"
    loop_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "project_id": "demo",
                "role": role,
                "objective": "compare current and draft",
                "review": "fail closed on infrastructure errors",
                "max_iterations": 1,
                "cases_sha256": "cases",
                "frozen_current_sha256": "current",
                "source_revision": "revision",
                "status": status,
                "iterations": [
                    {
                        "iteration": 1,
                        "run_report": {
                            "location_scope": "project_package",
                            "location": f"draft/.state/{role}/iterations/001-run.json",
                            "sha256": run_sha256,
                        },
                        "draft_fingerprint": "draft",
                        "decision": "blocked",
                        "route": "blocked",
                        "reason": "model gateway returned 403",
                        "evidence": [
                            {
                                "artifact": {
                                    "location_scope": "project_package",
                                    "location": f"draft/.state/{role}/iterations/001-run.json",
                                    "sha256": run_sha256,
                                }
                            },
                            {
                                "artifact": {
                                    "location_scope": "project_package",
                                    "location": f"draft/.state/{role}/iterations/001-role-review.json",
                                    "sha256": review_sha256,
                                }
                            },
                        ],
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return run_report, review_path, loop_path


def _active_artifact_test_context(root: Path, monkeypatch):
    from impl.core.active_artifacts import ActiveArtifactContext
    from impl.core.path_contract import PathResolver, PathRoots
    from impl.core.portable_artifact import PortableArtifactWriter

    project_root = root / "impl" / "projects" / "demo"
    roots = PathRoots(
        verifier_repo=root.resolve(),
        project_package=project_root.resolve(),
        knowledge_route=project_root.resolve(),
        artifact_package=project_root.resolve(),
    )

    class Spec:
        project_id = "demo"
        path_resolver = PathResolver(roots)

    context = ActiveArtifactContext(
        root=root,
        dotenv_path=root / ".env",
        environ={},
        writer=PortableArtifactWriter(),
    )
    monkeypatch.setattr(
        ActiveArtifactContext,
        "project_spec",
        lambda _self, project_id: Spec() if project_id == "demo" else None,
    )
    return context


def test_role_review_registry_does_not_bind_trusted_blocked_review_to_new_solidify(
    tmp_path: Path, monkeypatch
) -> None:
    from impl.core import draft_role_review
    from impl.core.active_artifacts import _validate_draft_role_review

    root = tmp_path / "verifier"
    _run_report, review_path, _loop_path = _blocked_role_fixture(root)
    context = _active_artifact_test_context(root, monkeypatch)
    checks: list[bool] = []

    def require_review(_spec, _role, _iteration, **kwargs):
        checks.append(kwargs["check_current_solidify"])
        return {}

    monkeypatch.setattr(draft_role_review, "require_draft_role_review", require_review)

    _validate_draft_role_review(context, review_path)

    assert checks == [False]


@pytest.mark.parametrize(
    ("loop_status", "stored_hash_matches", "accepted"),
    [
        ("blocked", True, True),
        ("blocked", False, False),
        ("active", True, False),
    ],
)
def test_stale_solidify_is_only_accepted_as_hash_linked_blocked_history(
    tmp_path: Path,
    monkeypatch,
    loop_status: str,
    stored_hash_matches: bool,
    accepted: bool,
) -> None:
    from impl.core import draft_role_review, solidify
    from impl.core.active_artifacts import _validate_draft_solidify

    root = tmp_path / "verifier"
    solidify_path = (
        root
        / "impl"
        / "projects"
        / "demo"
        / "draft"
        / ".state"
        / "judge"
        / "solidify.json"
    )
    solidify_path.parent.mkdir(parents=True, exist_ok=True)
    solidify_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_id": "demo",
                "role": "judge",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    actual_hash = hashlib.sha256(solidify_path.read_bytes()).hexdigest()
    stored_hash = actual_hash if stored_hash_matches else "different"
    run_report, _review_path, _loop_path = _blocked_role_fixture(
        root,
        status=loop_status,
        review_solidify_sha256=stored_hash,
    )
    context = _active_artifact_test_context(root, monkeypatch)

    monkeypatch.setattr(
        solidify,
        "require_solidify_receipt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("Draft Solidify receipt is stale: candidate_role_sha256 changed")
        ),
    )
    monkeypatch.setattr(
        draft_role_review,
        "require_draft_role_review",
        lambda *_args, **_kwargs: {
            "solidify_receipt_sha256": stored_hash,
            "run_report": str(run_report),
        },
    )

    if accepted:
        _validate_draft_solidify(context, solidify_path)
    else:
        with pytest.raises(ValueError, match="Draft Solidify receipt is stale"):
            _validate_draft_solidify(context, solidify_path)
