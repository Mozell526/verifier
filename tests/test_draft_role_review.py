from __future__ import annotations

import json
from pathlib import Path

import pytest

from impl.core import draft_role_review
from impl.core.draft_role_review import (
    JUDGE_REVIEW_CRITERIA,
    MOCK_REVIEW_CRITERIA,
    require_draft_role_review,
    write_draft_role_review,
)
from impl.core.path_contract import PathResolver, PathRoots
from impl.core.schema import ProjectSpec


def _project(tmp_path: Path, role: str, *, with_investigation: bool = True) -> ProjectSpec:
    verifier_root = tmp_path / "repo"
    project_root = verifier_root / "impl" / "projects" / "demo"
    (project_root / "draft" / ".state" / role / "iterations").mkdir(parents=True)
    investigation = project_root / "draft" / "investigation" / role
    investigation.mkdir(parents=True)
    assets = []
    if with_investigation:
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


def _report(spec: ProjectSpec, role: str, *, rows: list[dict] | None = None) -> Path:
    path = spec.project_package_path(
        f"draft/.state/{role}/iterations/001-run.json",
        field_path="test.run_report",
        must_exist=False,
    )
    path.write_text(json.dumps({
        "schema_version": 1,
        "run_status": "completed",
        "project_id": "demo",
        "role": role,
        "rows": rows if rows is not None else [{"case_key": "case-1"}],
    }), encoding="utf-8")
    return path


def _solidify(monkeypatch, tmp_path: Path, role: str, source_ids: list[str]) -> Path:
    path = tmp_path / f"{role}-solidify.json"
    path.write_text(json.dumps({"role": role, "required_source_ids": source_ids}), encoding="utf-8")
    monkeypatch.setattr(
        draft_role_review,
        "require_solidify_receipt",
        lambda spec, requested_role, **kwargs: {
            "role": requested_role,
            "required_source_ids": source_ids,
        },
    )
    monkeypatch.setattr(
        draft_role_review,
        "solidify_receipt_path",
        lambda spec, requested_role: path,
    )
    return path


def _criteria(role: str, *, status: str = "pass") -> list[dict]:
    criterion_ids = JUDGE_REVIEW_CRITERIA if role == "judge" else MOCK_REVIEW_CRITERIA
    return [{
        "criterion_id": criterion_id,
        "status": status,
        "evidence": ["iterations/001-run.json#rows[0]"],
        "finding": f"checked {criterion_id}",
    } for criterion_id in criterion_ids]


def _coverage(source_ids: list[str]) -> list[dict]:
    return [{
        "source_id": source_id,
        "evidence": ["iterations/001-run.json#rows[0]"],
    } for source_id in source_ids]


@pytest.mark.parametrize("role", ["judge", "mock"])
def test_role_review_round_trip_requires_complete_role_contract(
    tmp_path: Path, monkeypatch, role: str
):
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source-a", f"{role}:source-b"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role)

    path = write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="improved",
        route="promotion_checks",
        summary="Draft satisfies the role contract and does not regress.",
        criteria=_criteria(role),
        contract_coverage=_coverage(source_ids),
    )

    assert path.is_file()
    receipt = require_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="improved",
        route="promotion_checks",
    )
    assert receipt is not None
    assert [item["source_id"] for item in receipt["contract_coverage"]] == sorted(source_ids)


@pytest.mark.parametrize("role", ["judge", "mock"])
def test_role_review_rejects_missing_criterion_or_contract_source(
    tmp_path: Path, monkeypatch, role: str
):
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source-a", f"{role}:source-b"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role)

    with pytest.raises(ValueError, match="missing .* criteria"):
        write_draft_role_review(
            spec,
            role,
            1,
            run_report=report,
            decision="unchanged",
            route="solidify",
            summary="One role criterion was not reviewed.",
            criteria=_criteria(role)[:-1],
            contract_coverage=_coverage(source_ids),
        )

    with pytest.raises(ValueError, match="does not cover contract source IDs"):
        write_draft_role_review(
            spec,
            role,
            1,
            run_report=report,
            decision="unchanged",
            route="solidify",
            summary="One contract source was not reviewed.",
            criteria=_criteria(role),
            contract_coverage=_coverage(source_ids[:-1]),
        )


@pytest.mark.parametrize("role", ["judge", "mock"])
def test_improved_role_review_allows_non_relative_criterion_fail(
    tmp_path: Path, monkeypatch, role: str
):
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role)
    criteria = _criteria(role)
    criteria[0]["status"] = "fail"

    path = write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="improved",
        route="promotion_checks",
        summary="Net confident wins are positive; other criteria stay recorded.",
        criteria=criteria,
        contract_coverage=_coverage(source_ids),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["decision"] == "improved"
    assert payload["criteria"][0]["status"] == "fail"


@pytest.mark.parametrize("role", ["judge", "mock"])
def test_improved_role_review_rejects_failed_relative_improvement(
    tmp_path: Path, monkeypatch, role: str
):
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role)
    criteria = _criteria(role)
    criteria[-1]["status"] = "fail"

    with pytest.raises(ValueError, match="relative_improvement_no_regression to pass"):
        write_draft_role_review(
            spec,
            role,
            1,
            run_report=report,
            decision="improved",
            route="promotion_checks",
            summary="A scored regression must not be relabelled improved.",
            criteria=criteria,
            contract_coverage=_coverage(source_ids),
        )


def test_role_review_becomes_stale_after_run_or_solidify_change(tmp_path: Path, monkeypatch):
    role = "judge"
    spec = _project(tmp_path, role)
    source_ids = ["judge:source"]
    solidify_path = _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role)
    write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="unchanged",
        route="solidify",
        summary="More investigation is needed.",
        criteria=_criteria(role),
        contract_coverage=_coverage(source_ids),
    )

    report.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="run report hash changed"):
        require_draft_role_review(spec, role, 1, run_report=report)

    report = _report(spec, role)
    write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="unchanged",
        route="solidify",
        summary="More investigation is needed.",
        criteria=_criteria(role),
        contract_coverage=_coverage(source_ids),
    )
    solidify_path.write_text(
        json.dumps({"role": role, "required_source_ids": ["judge:new-source"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Solidify receipt changed"):
        require_draft_role_review(spec, role, 1, run_report=report)

    historical = require_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        check_current_solidify=False,
    )
    assert historical is not None
    assert [item["source_id"] for item in historical["contract_coverage"]] == source_ids

    monkeypatch.setattr(
        draft_role_review,
        "require_solidify_receipt",
        lambda spec, requested_role, **kwargs: (_ for _ in ()).throw(
            ValueError("current candidate made the Solidify receipt stale")
        ),
    )
    historical = require_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        check_current_solidify=False,
    )
    assert historical is not None


def test_role_review_rejects_fabricated_case_anchor(tmp_path: Path, monkeypatch):
    role = "judge"
    spec = _project(tmp_path, role)
    source_ids = ["judge:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role, rows=[{"case_key": "case-1"}])
    criteria = _criteria(role)
    criteria[0]["evidence"] = ["001-run.json#case-does-not-exist"]

    with pytest.raises(ValueError, match="absent from the run report"):
        write_draft_role_review(
            spec,
            role,
            1,
            run_report=report,
            decision="unchanged",
            route="solidify",
            summary="A criterion cites a case that the run report does not contain.",
            criteria=criteria,
            contract_coverage=_coverage(source_ids),
        )

    criteria[0]["evidence"] = ["001-run.json#case-1"]
    path = write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="unchanged",
        route="solidify",
        summary="All case anchors resolve to real run report cases.",
        criteria=criteria,
        contract_coverage=_coverage(source_ids),
    )
    assert path.is_file()


def test_no_investigation_asset_does_not_require_role_review(tmp_path: Path):
    spec = _project(tmp_path, "mock", with_investigation=False)
    report = _report(spec, "mock")
    assert require_draft_role_review(spec, "mock", 1, run_report=report) is None


@pytest.mark.parametrize(
    "row",
    [
        {
            "case_key": "judge-403",
            "current": {"evidence": ["llm_call_failed"]},
            "draft": {"evidence": ["llm_call_failed"]},
        },
        {
            "case_key": "mock-empty-query",
            "current": {"status": "pending"},
            "draft": {
                "status": "error",
                "error": {"type": "ValueError", "message": "empty query"},
            },
        },
    ],
)
def test_improved_role_review_rejects_terminal_role_execution_failure(
    tmp_path: Path, monkeypatch, row: dict
):
    role = "judge" if row["case_key"].startswith("judge") else "mock"
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role, rows=[row])

    with pytest.raises(ValueError, match="no comparable Draft sides"):
        write_draft_role_review(
            spec,
            role,
            1,
            run_report=report,
            decision="improved",
            route="promotion_checks",
            summary="Execution did not produce comparable outputs.",
            criteria=_criteria(role),
            contract_coverage=_coverage(source_ids),
        )


def test_loaded_improved_role_review_rejects_terminal_role_execution_failure(
    tmp_path: Path, monkeypatch
):
    role = "judge"
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(
        spec,
        role,
        rows=[{
            "case_key": "judge-403",
            "current": {"evidence": ["llm_call_failed"]},
            "draft": {"evidence": ["llm_call_failed"]},
        }],
    )
    review_path = write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="blocked",
        route="blocked",
        summary="The model service rejected both sides.",
        criteria=_criteria(role, status="not_evaluable"),
        contract_coverage=_coverage(source_ids),
    )
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["decision"] = "improved"
    payload["route"] = "promotion_checks"
    payload["criteria"] = _criteria(role)
    review_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="no comparable Draft sides"):
        require_draft_role_review(spec, role, 1, run_report=report)


def _healthy_judge_row(case_key: str) -> dict:
    return {
        "case_key": case_key,
        "current": {
            "evidence": ["capability_manifest"],
            "summary": {"fulfillment_status": "fulfilled"},
        },
        "current_runtime": {"environment": "missing", "authority_audit": {}},
        "draft": {
            "evidence": ["capability_manifest"],
            "summary": {"fulfillment_status": "fulfilled"},
        },
        "draft_runtime": {
            "environment": "ok",
            "authority_audit": {},
            "environment_snapshot_sha256": "abc",
        },
    }


def test_judge_current_missing_authority_environment_is_not_invalid():
    # Judge current 侧是生产部署，本身没有 authority runtime：environment=missing
    # 是正常状态（authority.md §8），不能把整个 current 侧判为执行失败。
    report = {
        "role": "judge",
        "rows": [_healthy_judge_row("judge-001")],
    }
    assert draft_role_review.run_report_invalid_sides(report) == []


def test_judge_draft_missing_authority_environment_is_invalid():
    # Authority 开启时 current 有 runtime、draft 没有，才是未接线。
    row = _healthy_judge_row("judge-002")
    row["current_runtime"] = {
        "environment": "ok",
        "authority_audit": {},
        "environment_snapshot_sha256": "abc",
    }
    row["draft_runtime"] = {"environment": "missing", "authority_audit": {}}
    report = {"role": "judge", "rows": [row]}
    assert draft_role_review.run_report_invalid_sides(report) == ["judge-002/draft"]


def test_judge_authority_off_missing_environment_is_not_invalid():
    row = _healthy_judge_row("judge-004")
    row["draft_runtime"] = {"environment": "missing", "authority_audit": {}}
    report = {"role": "judge", "rows": [row]}
    assert draft_role_review.run_report_invalid_sides(report) == []


def test_judge_current_missing_environment_still_invalid_on_llm_failure():
    # 即使 current 侧无 authority runtime，只要结果本身是执行失败
    # （LLM 调用失败等），仍判无效，防止用失败结果充当改善证据。
    row = _healthy_judge_row("judge-003")
    row["current"] = {"evidence": ["llm_call_failed"]}
    report = {"role": "judge", "rows": [row]}
    assert draft_role_review.run_report_invalid_sides(report) == ["judge-003/current"]


def test_improved_role_review_accepts_judge_current_without_authority_runtime(
    tmp_path: Path, monkeypatch
):
    role = "judge"
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    report = _report(spec, role, rows=[_healthy_judge_row("judge-001")])

    path = write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="improved",
        route="promotion_checks",
        summary="Draft judge improves business outcomes without regressions.",
        criteria=_criteria(role),
        contract_coverage=_coverage(source_ids),
    )
    assert path.is_file()


def test_improved_role_review_allows_partial_draft_abort(
    tmp_path: Path, monkeypatch
):
    role = "judge"
    spec = _project(tmp_path, role)
    source_ids = [f"{role}:source"]
    _solidify(monkeypatch, tmp_path, role, source_ids)
    abort_row = _healthy_judge_row("judge-abort")
    abort_row["draft"] = {"evidence": ["llm_call_failed"]}
    report = _report(
        spec,
        role,
        rows=[_healthy_judge_row("judge-ok"), abort_row],
    )

    path = write_draft_role_review(
        spec,
        role,
        1,
        run_report=report,
        decision="improved",
        route="promotion_checks",
        summary="One aborted Draft row is unscored and does not veto net wins.",
        criteria=_criteria(role),
        contract_coverage=_coverage(source_ids),
    )
    assert path.is_file()
