from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from impl.core import draft_role_review
from impl.core.draft_role_review import (
    MOCK_REVIEW_CRITERIA,
    write_draft_role_review,
)
from impl.core.path_contract import PathResolver, PathRoots
from impl.core.schema import JudgeResult, ProjectSpec, RunTrace


_SCRIPTS = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "draft" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
_SPEC = importlib.util.spec_from_file_location("test_draft_loop_script", _SCRIPTS / "draft_loop.py")
assert _SPEC is not None and _SPEC.loader is not None
draft_loop = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = draft_loop
_SPEC.loader.exec_module(draft_loop)
run_iteration = sys.modules["run_iteration"]

_UNSEEN_SPEC = importlib.util.spec_from_file_location(
    "test_draft_unseen_script", _SCRIPTS / "run_unseen.py"
)
assert _UNSEEN_SPEC is not None and _UNSEEN_SPEC.loader is not None
run_unseen = importlib.util.module_from_spec(_UNSEEN_SPEC)
sys.modules[_UNSEEN_SPEC.name] = run_unseen
_UNSEEN_SPEC.loader.exec_module(run_unseen)


def _project(
    tmp_path: Path, *, role: str = "mock", with_investigation: bool = False
) -> ProjectSpec:
    verifier_root = tmp_path / "repo"
    project_root = verifier_root / "impl" / "projects" / "demo"
    (project_root / "draft").mkdir(parents=True)
    (project_root / "attribute.py").write_text("production", encoding="utf-8")
    (project_root / "draft" / "attribute.py").write_text("candidate-1", encoding="utf-8")
    (project_root / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
    assets = []
    if with_investigation:
        (project_root / "draft" / "investigation" / role).mkdir(parents=True)
        assets.append({
            "asset_id": f"{role}_investigation",
            "kind": "investigation",
            "enabled": True,
            "roles": [role],
            "production_path": f"project://investigation/{role}",
            "candidate_path": f"project://draft/investigation/{role}",
            "replace": True,
        })
    roots = PathRoots(
        verifier_repo=verifier_root.resolve(),
        project_package=project_root.resolve(),
        knowledge_route=project_root.resolve(),
        artifact_package=project_root.resolve(),
    )
    return ProjectSpec(
        project_id="demo",
        name="demo",
        verifier={"assets": assets},
        path_roots=roots,
        path_resolver=PathResolver(roots),
    )


def test_iteration_side_clone_handles_mappingproxy_and_isolates_verifier(tmp_path: Path):
    from types import MappingProxyType

    spec = _project(tmp_path)
    spec.config_sources = MappingProxyType({})
    spec.verifier = {
        "roles": {
            "mock": {
                "draft": {"enabled": False, "module": "project://draft/mock.py"}
            }
        }
    }

    candidate = run_iteration._spec_for_side(spec, "mock", enabled=True)

    assert candidate.role_draft("mock")["enabled"] is True
    assert spec.role_draft("mock")["enabled"] is False
    assert candidate.config_sources is spec.config_sources
    assert candidate.path_resolver is spec.path_resolver


def test_frozen_iteration_warns_on_candidate_evidence_drift_and_audits_it(
    tmp_path: Path, monkeypatch
):
    spec = _project(tmp_path, role="mock", with_investigation=True)
    monkeypatch.setattr(run_iteration, "load_project", lambda project_id: spec)
    captured = {}
    staleness = {
        "policy": "warn",
        "source_revision": "revision-1",
        "current_source_revision": "revision-2",
        "source_revision_drifted": True,
        "warnings": [{
            "kind": "evidence_content_drift",
            "ref_id": "business-source",
            "expected": "old-hash",
            "actual": "new-hash",
            "message": "EvidenceRef content hash changed",
        }],
    }

    def fake_require_solidify(requested_spec, role, **kwargs):
        captured.update(kwargs)
        return {
            "schema_version": 2,
            "manifest_sha256": "manifest-hash",
            "role_contract_sha256": "contract-hash",
            "runtime_staleness": staleness,
        }

    def fake_run_serial(pending, role, runner, attempts, rows, progress_callback):
        rows["case-1"] = {"case_key": "case-1", "current": {}, "draft": {}}

    monkeypatch.setattr(run_iteration, "require_solidify_receipt", fake_require_solidify)
    monkeypatch.setattr(run_iteration, "_CaseRunner", lambda *args, **kwargs: object())
    monkeypatch.setattr(run_iteration, "_run_serial", fake_run_serial)

    report = run_iteration.run_frozen_iteration(
        "demo",
        "mock",
        [{"case_key": "case-1"}],
        health_check=False,
    )

    assert captured["business_source_staleness_policy"] == "warn"
    assert report["draft"]["solidify_receipt"]["runtime_staleness"] == staleness


def test_draft_loop_freezes_current_and_requires_review_between_iterations(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {
            "project_id": project_id,
            "role": role,
            "rows": cases,
            "run_status": "completed",
        },
    )
    cases = {"iteration_cases": [{"case_key": "case-1", "value": 1}]}

    state = draft_loop.start_loop(
        "demo",
        "mock",
        cases,
        objective="improve diagnosis",
        review="must be more accurate with no regression",
        max_iterations=3,
    )
    assert state.status == "active"
    draft_loop.run_iteration("demo", "mock")
    draft_loop.run_iteration("demo", "mock")
    iterations_dir = spec.project_package_path() / "draft" / ".state" / "mock" / "iterations"
    assert (iterations_dir / "001-run.json").is_file()
    assert (iterations_dir / "001-run-r2.json").is_file()
    assert len(draft_loop._read_state(draft_loop._state_path(spec, "mock")).iterations) == 1

    (spec.project_package_path() / "draft" / "attribute.py").write_text(
        "candidate-changed-before-review", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="awaits Harness review"):
        draft_loop.run_iteration("demo", "mock")
    (spec.project_package_path() / "draft" / "attribute.py").write_text(
        "candidate-1", encoding="utf-8"
    )

    reviewed = draft_loop.record_review(
        "demo",
        "mock",
        decision="unchanged",
        route="solidify",
        reason="same output",
        evidence=["iterations/001-run.json#rows[0]"],
    )
    assert reviewed.status == "active"
    (spec.project_package_path() / "draft" / "attribute.py").write_text("candidate-2", encoding="utf-8")
    draft_loop.run_iteration("demo", "mock")

    (spec.project_package_path() / "attribute.py").write_text(
        "production changed",
        encoding="utf-8",
    )
    draft_loop.record_review(
        "demo",
        "mock",
        decision="insufficient_evidence",
        route="investigate",
        reason="missing counterexample",
        evidence=["iterations/002-run.json#rows[0]"],
    )
    with pytest.raises(RuntimeError, match="frozen Current changed"):
        draft_loop.run_iteration("demo", "mock")


def test_draft_loop_records_source_revision_drift_without_blocking(tmp_path: Path, monkeypatch):
    """Business source revision change records drift but does not block iteration."""
    source_dir = tmp_path / "business-src"
    source_dir.mkdir()
    # Build spec with business_source in PathRoots from the start (frozen dataclass)
    verifier_root = tmp_path / "repo"
    project_root = verifier_root / "impl" / "projects" / "demo"
    (project_root / "draft").mkdir(parents=True)
    (project_root / "attribute.py").write_text("production", encoding="utf-8")
    (project_root / "draft" / "attribute.py").write_text("candidate-1", encoding="utf-8")
    (project_root / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
    roots = PathRoots(
        verifier_repo=verifier_root.resolve(),
        project_package=project_root.resolve(),
        knowledge_route=project_root.resolve(),
        artifact_package=project_root.resolve(),
        business_source=source_dir.resolve(),
    )
    spec = ProjectSpec(
        project_id="demo",
        name="demo",
        verifier={"assets": []},
        path_roots=roots,
        path_resolver=PathResolver(roots),
    )

    revisions = ["rev-aaa"]
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(draft_loop, "detect_source_revision", lambda path: revisions[0])
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {
            "project_id": project_id,
            "role": role,
            "rows": cases,
            "run_status": "completed",
        },
    )
    cases = {"iteration_cases": [{"case_key": "case-1", "value": 1}]}

    draft_loop.start_loop(
        "demo",
        "mock",
        cases,
        objective="test drift",
        review="review criteria",
        max_iterations=3,
    )
    # First iteration: no drift
    draft_loop.run_iteration("demo", "mock")
    report_1_path = spec.project_package_path() / "draft" / ".state" / "mock" / "iterations" / "001-run.json"
    report_1 = json.loads(report_1_path.read_text(encoding="utf-8"))
    assert report_1["source_revision_drift"]["business_source_revision_drifted"] is False

    # Review to unlock next iteration
    draft_loop.record_review(
        "demo",
        "mock",
        decision="unchanged",
        route="solidify",
        reason="baseline",
        evidence=["iterations/001-run.json#rows[0]"],
    )

    # Simulate business source advancing to a new commit
    revisions[0] = "rev-bbb"
    # Second iteration: should NOT raise, but should record drift
    draft_loop.run_iteration("demo", "mock")
    report_2_path = spec.project_package_path() / "draft" / ".state" / "mock" / "iterations" / "002-run.json"
    report_2 = json.loads(report_2_path.read_text(encoding="utf-8"))
    drift = report_2["source_revision_drift"]
    assert drift["business_source_revision_drifted"] is True
    assert drift["frozen_source_revision"] == "rev-aaa"
    assert drift["current_source_revision"] == "rev-bbb"


def test_draft_loop_only_marks_ready_after_evidenced_improvement(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {"rows": cases, "run_status": "completed"},
    )
    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-1"}]},
        objective="improve diagnosis",
        review="verified accuracy and no regression",
        max_iterations=2,
    )
    draft_loop.run_iteration("demo", "mock")
    state = draft_loop.record_review(
        "demo",
        "mock",
        decision="improved",
        route="promotion_checks",
        reason="draft identifies the verified mechanism while current does not",
        evidence=["iterations/001-run.json#rows[0]"],
    )
    assert state.status == "ready_for_promotion_checks"
    with pytest.raises(ValueError, match="not active"):
        draft_loop.run_iteration("demo", "mock")


def test_formal_attribute_run_rejects_runtime_infrastructure_failure():
    runtime = {
        "context": {
            "context_debug": {
                "errors": [{
                    "operation": "search_context_units",
                    "type": "ConnectionResetError",
                    "message": "connection reset",
                    "infrastructure": True,
                }]
            }
        },
        "evidence_registration_errors": [],
        "review_calls": [],
    }

    with pytest.raises(RuntimeError, match="draft attribute runtime invalid"):
        run_iteration._assert_formal_runtime_valid(
            "attribute", "draft", "case-1", runtime
        )
    assert run_iteration._formal_runtime_failures(
        "attribute",
        {
            "context": {
                "context_debug": {
                    "errors": [{
                        "operation": "load_context_units",
                        "type": "ContextNotFoundError",
                        "message": "missing",
                        "infrastructure": False,
                    }]
                }
            }
        },
    ) == []


def test_fulfilled_attribute_case_skips_environment_assembly():
    class FulfilledAttribute:
        def __init__(self):
            self.spec = ProjectSpec(project_id="demo", name="demo")
            self.configured = False

        def configure_execution_environment(self, _environment):
            self.configured = True

        def attribute_failure(self, trace, _judge):
            return {"trace_id": trace.trace_id, "status": "not_applicable"}

    implementation = FulfilledAttribute()
    result = run_iteration._run_role(
        "attribute",
        implementation,
        {
            "trace": RunTrace(trace_id="trace-fulfilled", project_id="demo"),
            "judge_result": JudgeResult(
                trace_id="trace-fulfilled",
                project_id="demo",
                overall_fulfillment={"status": "fulfilled"},
            ),
        },
    )
    assert result["status"] == "not_applicable"
    assert implementation.configured is False


def test_formal_judge_run_preserves_and_blocks_on_draft_context_governance():
    implementation = type("Judge", (), {
        "_last_judge_context": {
            "context_governance_report": {
                "snapshot": {"compiled_prompt_sha256": "prompt-hash"},
                "findings": [{"code": "output_contract_count"}],
                "gate": {"mode": "draft", "blocking": True},
            }
        }
    })()

    runtime = run_iteration._runtime_snapshot("judge", implementation)

    assert runtime["context_governance"]["snapshot"]["compiled_prompt_sha256"] == "prompt-hash"
    assert run_iteration._formal_runtime_failures("judge", runtime) == [
        "Draft Context Governance has open blocking findings"
    ]


def test_improved_review_rejects_completed_report_with_runtime_failure(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {
            "rows": [{
                "case_key": "case-1",
                "current_runtime": {},
                "draft_runtime": {
                    "evidence_registration_errors": ["embedding unavailable"]
                },
            }],
            "run_status": "completed",
        },
    )
    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-1"}]},
        objective="improve generation",
        review="must be better",
        max_iterations=2,
    )
    draft_loop.run_iteration("demo", "mock")

    with pytest.raises(ValueError, match="no comparable Draft sides"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="improved",
            route="promotion_checks",
            reason="looks better",
            evidence=["iterations/001-run.json#rows[0]"],
        )


def test_improved_review_rejects_terminal_role_output_failure(
    tmp_path: Path, monkeypatch
):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {
            "rows": [
                {
                    "case_key": "case-403",
                    "current": {"evidence": ["llm_call_failed"]},
                    "draft": {"evidence": ["llm_call_failed"]},
                    "current_runtime": {},
                    "draft_runtime": {},
                }
            ],
            "run_status": "completed",
        },
    )
    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-403"}]},
        objective="improve generation",
        review="must be better",
        max_iterations=2,
    )
    draft_loop.run_iteration("demo", "mock")

    with pytest.raises(ValueError, match="no comparable Draft sides"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="improved",
            route="promotion_checks",
            reason="cannot promote a 403 result",
            evidence=["iterations/001-run.json#rows[0]"],
        )


def test_draft_loop_validates_all_cases_before_writing_state(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)

    with pytest.raises(TypeError, match=r"case\[1\]"):
        draft_loop.start_loop(
            "demo",
            "mock",
            {"iteration_cases": [{"case_key": "valid"}, "invalid"]},
            objective="improve generation",
            review="must be better",
            max_iterations=2,
        )

    assert not (spec.project_package_path() / "draft" / ".state" / "mock" / "loop.json").exists()


def test_draft_loop_preserves_failed_iteration_and_requires_real_evidence(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)

    def fail_iteration(project_id, role, cases, **kwargs):
        callback = kwargs["progress_callback"]
        callback({
            "phase": "current_completed",
            "case_index": 0,
            "completed_rows": [],
            "partial_row": {"case_key": "case-1", "current": {"status": "done"}},
        })
        raise ConnectionError("embedding unavailable")

    monkeypatch.setattr(draft_loop, "run_frozen_iteration", fail_iteration)
    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-1"}]},
        objective="improve generation",
        review="must be better",
        max_iterations=2,
    )

    with pytest.raises(RuntimeError, match="partial facts preserved"):
        draft_loop.run_iteration("demo", "mock")

    state = draft_loop._read_state(
        spec.project_package_path() / "draft" / ".state" / "mock" / "loop.json"
    )
    assert len(state.iterations) == 1
    report_path = draft_loop._resolve_reference(
        spec, state.iterations[0].run_report, "test.run_report"
    )
    raw_state = __import__("json").loads(
        (
            spec.project_package_path()
            / "draft"
            / ".state"
            / "mock"
            / "loop.json"
        ).read_text(encoding="utf-8")
    )
    assert raw_state["schema_version"] == 2
    assert raw_state["iterations"][0]["run_report"]["location"] == (
        "draft/.state/mock/iterations/001-run.json"
    )
    assert raw_state["iterations"][0]["run_report"]["location_scope"] == "project_package"
    assert len(raw_state["iterations"][0]["run_report"]["sha256"]) == 64
    report = __import__("json").loads(report_path.read_text(encoding="utf-8"))
    assert report["run_status"] == "failed"
    assert report["partial_row"]["current"]["status"] == "done"

    with pytest.raises(ValueError, match="does not exist"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="blocked",
            route="blocked",
            reason="infrastructure failed",
            evidence=["missing.json"],
        )

    reviewed = draft_loop.record_review(
        "demo",
        "mock",
        decision="blocked",
        route="blocked",
        reason="infrastructure failed",
        evidence=[str(report_path)],
    )
    assert reviewed.status == "blocked"


def test_draft_loop_does_not_expose_stale_report_from_restarted_loop(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    state_dir = spec.project_package_path() / "draft" / ".state" / "mock"
    report_path = state_dir / "iterations" / "001-run.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text('{"run_status":"completed","stale":true}\n', encoding="utf-8")

    def inspect_before_new_result(project_id, role, cases, **kwargs):
        assert not report_path.exists()
        return {"rows": cases, "run_status": "completed"}

    monkeypatch.setattr(draft_loop, "run_frozen_iteration", inspect_before_new_result)
    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-1"}]},
        objective="improve generation",
        review="must be better",
        max_iterations=2,
    )
    draft_loop.run_iteration("demo", "mock")

    report = __import__("json").loads(report_path.read_text(encoding="utf-8"))
    assert report["run_status"] == "completed"
    assert "stale" not in report


def test_draft_loop_restart_archives_complete_previous_revision(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    state_dir = spec.project_package_path() / "draft" / ".state" / "mock"
    first_cases = {"iteration_cases": [{"case_key": "case-1", "value": 1}]}
    first = draft_loop.start_loop(
        "demo",
        "mock",
        first_cases,
        objective="first objective",
        review="first review",
        max_iterations=2,
    )
    iterations_dir = state_dir / "iterations"
    iterations_dir.mkdir(parents=True)
    old_report = iterations_dir / "001-run.json"
    old_review = iterations_dir / "001-role-review.json"
    old_report.write_text('{"run_status":"completed","revision":1}\n', encoding="utf-8")
    old_review.write_text('{"decision":"blocked","revision":1}\n', encoding="utf-8")
    solidify = state_dir / "solidify.json"
    solidify.write_text('{"receipt":"first"}\n', encoding="utf-8")
    old_loop_bytes = (state_dir / "loop.json").read_bytes()
    old_cases_bytes = (state_dir / "iteration-cases.json").read_bytes()
    old_report_bytes = old_report.read_bytes()
    old_review_bytes = old_review.read_bytes()

    second = draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-2", "value": 2}]},
        objective="second objective",
        review="second review",
        max_iterations=3,
        restart=True,
    )

    archive_dir = state_dir / "history" / "001"
    archive = __import__("json").loads(
        (archive_dir / "archive.json").read_text(encoding="utf-8")
    )
    assert archive["project_id"] == "demo"
    assert archive["role"] == "mock"
    assert archive["revision"] == 1
    assert archive["loop_status"] == first.status
    archived_paths = {item["path"] for item in archive["files"]}
    assert {
        "loop.json",
        "iteration-cases.json",
        "iterations/001-run.json",
        "iterations/001-role-review.json",
        "solidify.json",
    } <= archived_paths
    assert (archive_dir / "loop.json").read_bytes() == old_loop_bytes
    assert (archive_dir / "iteration-cases.json").read_bytes() == old_cases_bytes
    assert (archive_dir / "iterations" / "001-run.json").read_bytes() == old_report_bytes
    assert (archive_dir / "iterations" / "001-role-review.json").read_bytes() == old_review_bytes
    assert (archive_dir / "solidify.json").read_text(encoding="utf-8") == '{"receipt":"first"}\n'
    assert not (state_dir / "iterations").exists()
    assert solidify.read_text(encoding="utf-8") == '{"receipt":"first"}\n'
    assert second.objective == "second objective"
    assert second.iterations == []

    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-3", "value": 3}]},
        objective="third objective",
        review="third review",
        max_iterations=1,
        restart=True,
    )
    assert (state_dir / "history" / "001" / "archive.json").is_file()
    assert (state_dir / "history" / "002" / "archive.json").is_file()


def test_unseen_runner_uses_common_frozen_protocol_for_mock(monkeypatch, capsys):
    captured = {}

    def fake_run(project_id, role, cases):
        captured.update(project_id=project_id, role=role, cases=cases)
        return {"case_count": len(cases), "rows": [{"case_key": "mock-1"}]}

    monkeypatch.setattr(run_unseen, "run_frozen_iteration", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_unseen.py",
            "--project",
            "demo",
            "--role",
            "mock",
            "--cases",
            '[{"case_key":"mock-1","scenario":"boundary"}]',
        ],
    )

    assert run_unseen.main() == 0
    assert captured == {
        "project_id": "demo",
        "role": "mock",
        "cases": [{"case_key": "mock-1", "scenario": "boundary"}],
    }
    output = capsys.readouterr().out
    assert '"case_count": 1' in output


def test_draft_loop_requires_matching_cited_role_review_when_investigation_exists(
    tmp_path: Path, monkeypatch
):
    spec = _project(tmp_path, role="mock", with_investigation=True)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {
            "project_id": project_id,
            "role": role,
            "rows": cases,
            "run_status": "completed",
        },
    )
    solidify_path = (
        spec.project_package_path() / "draft" / ".state" / "mock" / "solidify.json"
    )
    solidify_path.parent.mkdir(parents=True, exist_ok=True)
    source_ids = ["business_value:target-client-analysis"]
    solidify_path.write_text(
        json.dumps({"role": "mock", "required_source_ids": source_ids}),
        encoding="utf-8",
    )
    fake_receipt = {
        "role": "mock",
        "required_source_ids": source_ids,
    }
    monkeypatch.setattr(
        "impl.core.solidify.require_solidify_receipt",
        lambda requested_spec, requested_role, **kwargs: fake_receipt,
    )
    monkeypatch.setattr(
        "impl.core.draft_pending.assert_run_allowed",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        draft_role_review,
        "require_solidify_receipt",
        lambda requested_spec, requested_role, **kwargs: fake_receipt,
    )
    monkeypatch.setattr(
        draft_role_review,
        "solidify_receipt_path",
        lambda requested_spec, requested_role: solidify_path,
    )

    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-1"}]},
        objective="improve generated business-user coverage",
        review="compare the frozen Current and Draft without regression",
        max_iterations=2,
    )
    draft_loop.run_iteration("demo", "mock")

    with pytest.raises(ValueError, match="role_review|role review"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="unchanged",
            route="solidify",
            reason="review receipt is still missing",
            evidence=["iterations/001-run.json#rows[0]"],
        )

    report = (
        spec.project_package_path()
        / "draft"
        / ".state"
        / "mock"
        / "iterations"
        / "001-run.json"
    )
    criteria = [
        {
            "criterion_id": criterion_id,
            "status": "pass",
            "evidence": ["iterations/001-run.json#rows[0]"],
            "finding": f"checked {criterion_id}",
        }
        for criterion_id in MOCK_REVIEW_CRITERIA
    ]
    review_path = write_draft_role_review(
        spec,
        "mock",
        1,
        run_report=report,
        decision="unchanged",
        route="solidify",
        summary="The frozen evidence is valid but does not yet prove improvement.",
        criteria=criteria,
        contract_coverage=[
            {
                "source_id": source_ids[0],
                "evidence": ["iterations/001-run.json#rows[0]"],
            }
        ],
    )

    with pytest.raises(ValueError, match="decision does not match"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="regressed",
            route="solidify",
            reason="does not match the role review receipt",
            evidence=[
                "iterations/001-run.json#rows[0]",
                "iterations/001-role-review.json",
            ],
        )

    with pytest.raises(ValueError, match="must cite the validated role review"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="unchanged",
            route="solidify",
            reason="receipt exists but is not cited",
            evidence=["iterations/001-run.json#rows[0]"],
        )

    with pytest.raises(ValueError, match="rendered comparison table"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="unchanged",
            route="solidify",
            reason="role review cited but the comparison table is missing",
            evidence=[
                "iterations/001-run.json#rows[0]",
                "iterations/001-role-review.json",
            ],
        )

    table_path = (
        spec.project_package_path()
        / "draft"
        / ".state"
        / "mock"
        / "iterations"
        / "001-run-comparison-table.md"
    )
    table_path.write_text(
        "| case | query 输入 | live 输出 | production mock 结果 | draft mock 结果 | harness 分析 |\n"
        "|---|---|---|---|---|---|\n"
        "| case-1 | q | out | a | b | - |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="harness analysis is not filled"):
        draft_loop.record_review(
            "demo",
            "mock",
            decision="unchanged",
            route="solidify",
            reason="table exists but the harness analysis is still a placeholder",
            evidence=[
                "iterations/001-run.json#rows[0]",
                "iterations/001-role-review.json",
                "iterations/001-run-comparison-table.md",
            ],
        )

    table_path.write_text(
        "| case | query 输入 | live 输出 | production mock 结果 | draft mock 结果 | harness 分析 |\n"
        "|---|---|---|---|---|---|\n"
        "| case-1 | q | out | a | b | 两侧生成覆盖一致，无差异 |\n",
        encoding="utf-8",
    )
    state = draft_loop.record_review(
        "demo",
        "mock",
        decision="unchanged",
        route="solidify",
        reason="role review, run report and comparison table are all cited",
        evidence=[
            "iterations/001-run.json#rows[0]",
            "iterations/001-role-review.json",
            "iterations/001-run-comparison-table.md",
        ],
    )
    assert state.status == "active"
    assert review_path.is_file()


def test_draft_loop_run_blocked_by_unresolved_gate_feedback(tmp_path: Path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)
    monkeypatch.setattr(
        draft_loop,
        "run_frozen_iteration",
        lambda project_id, role, cases, **kwargs: {"rows": cases, "run_status": "completed"},
    )
    draft_loop.start_loop(
        "demo",
        "mock",
        {"iteration_cases": [{"case_key": "case-1"}]},
        objective="improve generation",
        review="must be better",
        max_iterations=2,
    )
    feedback = (
        spec.project_package_path()
        / "draft"
        / ".state"
        / "mock"
        / "solidify-gate-feedback.json"
    )
    feedback.write_text('{"gate":"AUTHORITY_GATE"}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="unresolved Draft gate feedback"):
        draft_loop.run_iteration("demo", "mock")

    feedback.unlink()
    draft_loop.run_iteration("demo", "mock")


def test_judge_comparison_table_requires_spec_anchor_and_matching_cases(tmp_path: Path):
    report_path = tmp_path / "001-run.json"
    report_path.write_text(
        json.dumps({
            "run_status": "completed",
            "rows": [{"case_key": "case-1"}, {"case_key": "case-2"}],
        }),
        encoding="utf-8",
    )
    table_path = tmp_path / "001-run-comparison-table.md"
    header = (
        "| case | query 输入 | live 输出 | production judge 结果 | draft judge 结果 | harness 分析 |\n"
        "|---|---|---|---|---|---|\n"
    )

    table_path.write_text(
        header + "| case-1 | q | out | F | NF | draft 对，反面 #1 如实拒绝不算办成 |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match the frozen run report"):
        draft_loop._require_comparison_table("judge", report_path)

    table_path.write_text(
        header
        + "| case-1 | q | out | F | NF | draft 对，反面 #1 如实拒绝不算办成 |\n"
        + "| case-2 | q | out | F | NF | 两侧都对 |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must cite fulfilled.md"):
        draft_loop._require_comparison_table("judge", report_path)

    table_path.write_text(
        header
        + "| case-1 | q | out | F | NF | draft 对，反面 #1 如实拒绝不算办成 |\n"
        + "| case-2 | q | out | F | NF | 歧义-缺 normative 资料：术语表未裁决 |\n",
        encoding="utf-8",
    )
    assert draft_loop._require_comparison_table("judge", report_path) == table_path

    table_path.write_text(
        header
        + "| case-1 | q | out | F | NF | draft 对，反面 #1 如实拒绝不算办成 |\n"
        + "| case-2 | q | out | F | NF | 检索缺口：空间资料在，本轮未 Load |\n",
        encoding="utf-8",
    )
    assert draft_loop._require_comparison_table("judge", report_path) == table_path

    table_path.write_text(
        header
        + "| case-1 | q | out | F | NF | draft 对，反面 #1 如实拒绝不算办成 |\n"
        + "| case-2 | q | out | F | NF | 不计分。人判不完：无尺子 |\n",
        encoding="utf-8",
    )
    assert draft_loop._require_comparison_table("judge", report_path) == table_path


def test_draft_iteration_classifies_balance_and_auth_as_unrecoverable_provider_failures():
    insufficient_balance = {
        "error": None,
        "payload": {"reasoning_summary": "LLM 调用失败: HTTP 402 Insufficient Balance"},
        "runtime": {},
    }
    rate_quota = {
        "error": "Throttling.RateQuota: Requests rate limit exceeded",
        "payload": {},
        "runtime": {},
    }

    assert run_iteration._unrecoverable_provider_failure(insufficient_balance) in {
        "insufficient balance",
        "http 402",
    }
    assert run_iteration._unrecoverable_provider_failure(rate_quota) is None
    assert run_iteration._is_endpoint_failure(rate_quota) is True


def test_parallel_draft_iteration_aborts_pending_cases_after_unrecoverable_provider_failure(
    monkeypatch,
):
    attempted = []
    abort_event = __import__("threading").Event()

    def fail_case(
        role, runner, attempts, index, raw_case, case, shared_abort,
        current_completed=None,
    ):
        attempted.append(index)
        shared_abort.set()
        raise run_iteration.UnrecoverableProviderFailure("insufficient balance")

    monkeypatch.setattr(run_iteration, "_run_one_case", fail_case)
    pending = [(index, {"case_key": str(index)}, {}) for index in range(30)]

    with pytest.raises(run_iteration.UnrecoverableProviderFailure, match="provider failure|insufficient balance"):
        run_iteration._run_parallel(
            pending,
            "judge",
            object(),
            3,
            {},
            None,
            8,
            abort_event,
        )

    assert abort_event.is_set()
    assert len(attempted) < len(pending)


def test_llm_preflight_reuses_public_router_health(monkeypatch):
    import impl.core.llm_client as llm_client_module

    class FakeRouter:
        probe_wait_seconds = 10.0

        def __init__(self):
            self.refresh_count = 0

        def refresh_health_if_stale(self):
            self.refresh_count += 1

        def active_endpoint_names(self):
            return []

    router = FakeRouter()

    class FakeClient:
        def __init__(self, role):
            assert role == "judge"
            self.llm_router = router

        def _validate_config(self):
            return None

    monkeypatch.setattr(llm_client_module, "LlmClient", FakeClient)

    with pytest.raises(RuntimeError, match="all configured endpoints are cooling"):
        run_iteration._probe_llm_endpoint("judge")

    assert router.refresh_count == 1


def test_side_endpoint_failure_does_not_retry_whole_case(monkeypatch):
    calls = []

    def fail_once(role, runner, side, case):
        calls.append(side)
        return {
            "payload": {"status": "error", "reasoning_summary": "LLM 调用失败: 503"},
            "runtime": {},
            "elapsed": 0.01,
            "error": "Service temporarily unavailable (503)",
        }

    monkeypatch.setattr(run_iteration, "_run_side_once", fail_once)

    result = run_iteration._run_side_with_retry(
        "judge", object(), 4, "draft", {},
    )

    assert result["error"] is not None
    assert calls == ["draft"]


def test_one_case_persists_current_before_draft_finishes(monkeypatch):
    events = []

    def fake_side(role, runner, attempts, side, case, abort_event=None):
        if side == "current":
            return {
                "payload": {"overall_fulfillment": {"status": "fulfilled"}},
                "runtime": {},
                "elapsed": 1.25,
                "error": None,
            }
        assert events and events[0]["current_metrics"]["elapsed_seconds"] == 1.25
        raise RuntimeError("draft still running")

    monkeypatch.setattr(run_iteration, "_run_side_with_retry", fake_side)
    monkeypatch.setattr(run_iteration, "_assert_formal_runtime_valid", lambda *args: None)

    with pytest.raises(RuntimeError, match="draft still running"):
        run_iteration._run_one_case(
            "judge",
            object(),
            1,
            0,
            {"case_key": "case-1"},
            {},
            current_completed=events.append,
        )

    assert events[0]["case_key"] == "case-1"
    assert "draft" not in events[0]


def test_draft_loop_failed_report_preserves_all_parallel_current_rows(tmp_path, monkeypatch):
    spec = _project(tmp_path)
    monkeypatch.setattr(draft_loop, "load_project", lambda project_id: spec)

    def fail_after_currents(project_id, role, cases, **kwargs):
        callback = kwargs["progress_callback"]
        callback({
            "phase": "current_completed",
            "case_index": 0,
            "completed_rows": [],
            "partial_row": {"case_key": "case-1", "current": {"status": "done"}},
        })
        callback({
            "phase": "current_completed",
            "case_index": 1,
            "completed_rows": [],
            "partial_row": {"case_key": "case-2", "current": {"status": "done"}},
        })
        raise TimeoutError("draft side timed out")

    monkeypatch.setattr(draft_loop, "run_frozen_iteration", fail_after_currents)
    draft_loop.start_loop(
        "demo", "mock",
        {"iteration_cases": [{"case_key": "case-1"}, {"case_key": "case-2"}]},
        objective="improve", review="must improve", max_iterations=1,
    )

    with pytest.raises(RuntimeError, match="partial facts preserved"):
        draft_loop.run_iteration("demo", "mock", workers=2)

    report = json.loads(
        (spec.project_package_path() / "draft" / ".state" / "mock" / "iterations" / "001-run.json")
        .read_text(encoding="utf-8")
    )
    assert [row["case_key"] for row in report["in_progress_rows"]] == ["case-1", "case-2"]


def test_resume_rejects_stale_fingerprints(tmp_path):
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({
        "frozen_cases_sha256": "cases-hash",
        "current_fingerprint": "old-current",
        "draft_fingerprint": "old-draft",
        "runner_fingerprint": "old-runner",
        "rows": [{
            "case_key": "c1",
            "current": {},
            "draft": {},
            "current_runtime": {},
            "draft_runtime": {},
        }],
    }), encoding="utf-8")
    with pytest.raises(RuntimeError, match="different current_fingerprint"):
        run_iteration._load_resume_rows(
            partial,
            "cases-hash",
            {
                "current_fingerprint": "new-current",
                "draft_fingerprint": "old-draft",
                "runner_fingerprint": "old-runner",
            },
        )


def test_resume_accepts_matching_fingerprints(tmp_path):
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({
        "frozen_cases_sha256": "cases-hash",
        "current_fingerprint": "fp",
        "draft_fingerprint": "fp",
        "runner_fingerprint": "fp",
        "rows": [{
            "case_key": "c1",
            "current": {"overall_fulfillment": {"status": "fulfilled"}},
            "draft": {"overall_fulfillment": {"status": "not_evaluable"}},
            "current_runtime": {"environment": "ok"},
            "draft_runtime": {"environment": "ok"},
        }],
    }), encoding="utf-8")
    resumed = run_iteration._load_resume_rows(
        partial,
        "cases-hash",
        {
            "current_fingerprint": "fp",
            "draft_fingerprint": "fp",
            "runner_fingerprint": "fp",
        },
    )
    assert list(resumed) == ["c1"]
