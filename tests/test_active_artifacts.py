from __future__ import annotations

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
