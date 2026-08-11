from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from impl.core.authority_gate import apply_authority_gate
from impl.core.authority_investigation_gates import (
    CLAIM_INDEX_RELATIVE_PATH,
    load_and_validate_authority_claim_index,
)
from impl.core.context.embedding import DeterministicHashEmbeddingProvider
from impl.core.authority_environment import build_authority_environment
from impl.core.authority_tool import build_authority_resolve_tool
from impl.core.draft_gate_feedback import analyze_judge_gate_obligations
from impl.core.project_loader import load_project, resolve_role_assets
from impl.core.schema import (
    AuthorityResolution,
    BusinessExpectation,
    FulfillmentAssessment,
    JudgeResult,
)
from impl.core.schema.investigation_judge import load_authority_investigation_report
from impl.core.solidify import write_solidify_probe_result


# 旧链路调查内部字段（AuthorityAnalysis/CausalChain/SourceClaim/evidence_ref_ids/
# causal_reasoning）不允许泄漏到 runtime 上下文；保留该断言以防回退。
FORBIDDEN_RUNTIME_FIELDS = (
    "source_claims",
    "causal_chain",
    "evidence_ref_ids",
    "causal_reasoning",
)

_AUTHORITY_REPORT_RELATIVE = "docs/authority-investigation-report.json"


def _load_authority_report(spec):
    """读取冻结权威调查报告：调查期物化的证据空间（资料 + 覆盖缺口）。

    与 runtime 上下文同源（investigate-authority-judge.md §13）：固定逻辑路径的
    artifact，校验后作为 authority.resolve 的检索空间。
    """
    selected = [
        item
        for item in resolve_role_assets(spec, "judge", use_candidate=True)
        if item["mapping"].kind == "investigation"
    ]
    if len(selected) != 1:
        raise RuntimeError(
            "Authority report requires exactly one judge investigation package, "
            f"got {len(selected)}"
        )
    path = Path(selected[0]["path"]) / _AUTHORITY_REPORT_RELATIVE
    if not path.is_file():
        raise FileNotFoundError(f"Authority investigation report not found: {path}")
    return load_authority_investigation_report(path)


def _enforcement_check(gap, snapshot_sha256: str) -> dict[str, Any]:
    """§8：assessment 依赖 unresolved 的 authority.resolve → not_evaluable。

    用报告的覆盖缺口构造一次 unresolved resolve 的 audit（reason=缺口原因、
    required_evidence=缺料清单），走真实运行时 gate；验证"已知没查清 →
    not_evaluable（依据不充分）"，缺料随 evidence 挂入，不硬凑结论。
    """
    analysis_id = gap.gap_id
    call_id = f"probe:{analysis_id}"
    result = JudgeResult(
        trace_id=f"solidify:{analysis_id}",
        project_id="client_search",
        business_expectations=[
            BusinessExpectation(
                expectation_id=f"probe:{analysis_id}",
                blocking=True,
            )
        ],
        fulfillment_assessments=[
            FulfillmentAssessment(
                expectation_id=f"probe:{analysis_id}",
                status="fulfilled",
                score=1.0,
                confidence=1.0,
                authority_tool_call_ids=[call_id],
            )
        ],
    )
    apply_authority_gate(
        result,
        tool_audit={
            call_id: {
                "resolution": AuthorityResolution(
                    status="unresolved",
                    statement="",
                    reason=gap.gap_reason,
                    basis_evidence_ref_ids=tuple(gap.basis_source_ref_ids),
                    required_evidence=tuple(gap.required_evidence),
                ),
                "environment_snapshot_sha256": snapshot_sha256,
            }
        },
    )
    return {
        "without_decisive_evidence": result.fulfillment_assessments[0].status,
    }


_AUTHORITY_PROBE_QUESTIONS = {
    "enum_space:orphanType": (
        "在 client_search 当前启用的客户搜索字段定义中，orphanType 字段的正式合法枚举值空间是什么？"
    ),
    "operator_support:familyInfo.familyclientbirthday": (
        "在 client_search 当前启用的字段定义与 enhanced_rules 同时适用时，"
        "familyInfo.familyclientbirthday 字段正式支持哪些查询操作符；若资料声明冲突，"
        "当前资料是否足以确定唯一生效规则？"
    ),
    "value_mapping:orphanType:孤儿单": (
        "在 client_search 的正式业务口径（不是仅描述当前 parser 配置行为）中，"
        "用户表达“孤儿单”时应正确映射为哪个 orphanType 正式枚举值；当前资料是否足以确定唯一映射？"
    ),
}


def _run_authority_replay(authority_env, probes) -> dict[str, Any]:
    """通过正式 authority.resolve 重放冻结 Subject，不向请求注入预期状态。"""
    authority_tool = build_authority_resolve_tool(authority_env)
    results = []
    for probe in probes:
        subject_id = str(probe["subject_id"])
        question = _AUTHORITY_PROBE_QUESTIONS.get(subject_id)
        if not question:
            raise ValueError(f"Authority probe lacks a decision question: {subject_id}")
        result = authority_tool._execute(question)
        call_id = str(result.get("tool_call_id") or "")
        audit = authority_tool.audit.get(call_id)
        results.append({
            "probe_id": str(probe.get("probe_id") or ""),
            "subject_id": subject_id,
            "status": str(result.get("status") or ""),
            "statement": str(result.get("statement") or ""),
            "reason": str(result.get("reason") or ""),
            "tool_call_id": call_id,
            "tool_audit_present": bool(audit),
            "environment_snapshot_sha256": (
                str((audit or {}).get("environment_snapshot_sha256") or "")
            ),
            "basis_evidence_ref_ids": list(result.get("basis_evidence_ref_ids") or []),
            "required_evidence": list(result.get("required_evidence") or []),
        })
    return {"probe_results": results}



def _four_quadrant_probe() -> dict[str, Any]:
    """Run the generic gate against the four Authority availability/outcome quadrants.

    This is a control-plane probe: it does not fabricate business truth or call the
    model. It checks that the gate attributes only observable evidence and applies
    the agreed penalty boundary.
    """
    common = {
        "business_expectations": [{"expectation_id": "core", "blocking": True}],
        "fulfillment_assessments": [{
            "expectation_id": "core", "status": "fulfilled",
            "authority_tool_call_ids": [],
        }],
        "overall_fulfillment": {"status": "fulfilled"},
    }
    cases = {
        "Q1_available_supported": ({
            "subject": "subject:q1", "authority_required": True,
            "authority_availability": "available", "blocking_expectation_ids": ["core"],
        }, {"authority_tool_call_ids": ["call-q1"], "authority_audit": {
            "call-q1": {"resolution": {"status": "supported"}}
        }}, {"status": "fulfilled", "authority_tool_call_ids": ["call-q1"]}),
        "Q2_available_gap": ({
            "subject": "subject:q2", "authority_required": True,
            "authority_availability": "available", "blocking_expectation_ids": ["core"],
        }, {"authority_tool_call_ids": ["call-q2"], "authority_audit": {
            "call-q2": {"resolution": {"status": "gap_only"}}
        }}, {"status": "not_evaluable", "authority_tool_call_ids": ["call-q2"]}),
        "Q3_unavailable_material_backed": ({
            "subject": "subject:q3", "authority_required": True,
            "authority_availability": "unavailable", "compact_material_backed": True,
            "blocking_expectation_ids": ["core"],
        }, {}, {"status": "fulfilled", "authority_tool_call_ids": []}),
        "Q4_unavailable_gap": ({
            "subject": "subject:q4", "authority_required": True,
            "authority_availability": "unavailable", "blocking_expectation_ids": ["core"],
        }, {}, {"status": "not_evaluable", "authority_tool_call_ids": []}),
    }
    results = {}
    for name, (obligation, runtime, assessment) in cases.items():
        payload = {**common, "fulfillment_assessments": [
            {"expectation_id": "core", **assessment}
        ], "overall_fulfillment": {"status": assessment["status"]}}
        gate = analyze_judge_gate_obligations(
            result=payload, runtime=runtime, obligations=[obligation]
        )
        results[name] = gate
    passed = (
        results["Q1_available_supported"]["status"] == "passed"
        and results["Q2_available_gap"]["status"] == "passed"
        and results["Q3_unavailable_material_backed"]["status"] == "passed"
        and not results["Q3_unavailable_material_backed"]["findings"]
        and results["Q4_unavailable_gap"]["status"] == "failed"
        and results["Q4_unavailable_gap"]["finding_counts"].get("availability_miss") == 1
    )
    return {"status": "succeeded" if passed else "failed", "quadrants": results}


def _obligation_gate_probe() -> dict[str, Any]:
    """Prove the Harness gate sees final-model failures, not just asset wiring.

    These are generic synthetic outputs.  They intentionally avoid client_search
    case text and validate only observable Judge topology/Authority consumption.
    """
    call_id = "authority.client_search.synthetic"
    healthy = analyze_judge_gate_obligations(
        result={
            "business_expectations": [
                {"expectation_id": "core", "blocking": True},
                {"expectation_id": "safe", "blocking": False},
            ],
            "fulfillment_assessments": [
                {
                    "expectation_id": "core",
                    "status": "not_evaluable",
                    "authority_tool_call_ids": [call_id],
                },
                {
                    "expectation_id": "safe",
                    "status": "fulfilled",
                    "authority_tool_call_ids": [],
                },
            ],
            "overall_fulfillment": {"status": "not_evaluable"},
        },
        runtime={
            "authority_tool_call_ids": [call_id],
            "authority_audit": {call_id: {"resolution": {"status": "unresolved"}}},
        },
        obligations=[{
            "subject": "synthetic:conflict",
            "trigger": "conflicting_materials",
            "authority_required": True,
            "blocking_expectation_ids": ["core"],
            "expected_non_blocking_expectation_ids": ["safe"],
        }],
    )
    missing_call = analyze_judge_gate_obligations(
        result={
            "business_expectations": [{"expectation_id": "core", "blocking": True}],
            "fulfillment_assessments": [{
                "expectation_id": "core",
                "status": "fulfilled",
                "authority_tool_call_ids": [],
            }],
            "overall_fulfillment": {"status": "fulfilled"},
        },
        runtime={},
        obligations=[{
            "subject": "synthetic:missing-carrier",
            "trigger": "missing_semantic_carrier",
            "authority_required": True,
            "blocking_expectation_ids": ["core"],
        }],
    )
    tool_failure = analyze_judge_gate_obligations(
        result={
            "business_expectations": [{"expectation_id": "core", "blocking": True}],
            "fulfillment_assessments": [{
                "expectation_id": "core",
                "status": "not_evaluable",
                "authority_tool_call_ids": [call_id],
            }],
            "overall_fulfillment": {"status": "not_evaluable"},
        },
        runtime={
            "authority_tool_call_ids": [call_id],
            "authority_audit": {call_id: {"tool_failure": True}},
        },
        obligations=[{
            "subject": "synthetic:tool-failure",
            "trigger": "operator_contract_conflict",
            "authority_required": True,
            "blocking_expectation_ids": ["core"],
        }],
    )
    bad_topology = analyze_judge_gate_obligations(
        result={
            "business_expectations": [
                {"expectation_id": "core", "blocking": True},
                {"expectation_id": "safe", "blocking": True},
            ],
            "fulfillment_assessments": [
                {"expectation_id": "core", "status": "not_evaluable", "authority_tool_call_ids": [call_id]},
                {"expectation_id": "safe", "status": "fulfilled", "authority_tool_call_ids": []},
            ],
            "overall_fulfillment": {"status": "not_evaluable"},
        },
        runtime={
            "authority_tool_call_ids": [call_id],
            "authority_audit": {call_id: {"resolution": {"status": "unresolved"}}},
        },
        obligations=[{
            "subject": "synthetic:boundary",
            "trigger": "missing_semantic_carrier",
            "authority_required": True,
            "blocking_expectation_ids": ["core"],
            "expected_non_blocking_expectation_ids": ["safe"],
        }],
    )
    detected = {
        "healthy_passed": healthy["status"] == "passed",
        "not_called": missing_call["finding_counts"].get("not_called") == 1,
        "tool_failure": tool_failure["finding_counts"].get("tool_failure") == 1,
        "bad_topology": bad_topology["finding_counts"].get("safety_expectation_marked_blocking") == 1,
    }
    return {
        "status": "succeeded" if all(detected.values()) else "failed",
        "detected": detected,
        "examples": {
            "healthy": healthy,
            "missing_call": missing_call,
            "tool_failure": tool_failure,
            "bad_topology": bad_topology,
        },
    }

def build_probe_payload() -> dict[str, Any]:
    spec = load_project("client_search")
    report = _load_authority_report(spec)
    assets = resolve_role_assets(spec, "judge", use_candidate=True)
    investigation_path = Path(next(
        item["path"] for item in assets if item["mapping"].asset_id == "judge_investigation"
    ))
    claim_gate = load_and_validate_authority_claim_index(
        investigation_path / CLAIM_INDEX_RELATIVE_PATH,
        evidence_ref_ids={material.source_ref_id for material in report.materials},
        coverage_gaps={item.gap_id: item for item in report.coverage_gaps},
    )
    business_contract = next(
        (
            dict(item.get("metadata") or {})
            for item in assets
            if item["mapping"].asset_id == "judge_business_contract"
        ),
        {},
    )
    authority_env = build_authority_environment(
        spec,
        role="judge",
        use_candidate=True,
        embedding_provider=DeterministicHashEmbeddingProvider(),
        trace_id="solidify-probe",
        case_id="",
    )
    snapshot_sha256 = authority_env.environment_snapshot_sha256
    authority_runtime_replay = _run_authority_replay(authority_env, claim_gate["probes"])
    obligation_gate = _obligation_gate_probe()
    four_quadrant_gate = _four_quadrant_probe()
    authority_checks = {}
    for gap in report.coverage_gaps:
        authority_checks[gap.gap_id] = {
            "analysis_id": gap.gap_id,
            "dimension_ids": list(gap.dimension_ids),
            "basis_source_ref_ids": list(gap.basis_source_ref_ids),
            "required_evidence": list(gap.required_evidence),
            "case_time": _enforcement_check(gap, snapshot_sha256),
        }
    succeeded = bool(
        business_contract.get("product_expectation_ids")
        and business_contract.get("dimensions")
        and business_contract.get("dimension_expectation_ids")
        and report.materials
        and claim_gate["probes"]
        and claim_gate["claims_sha256"]
        and snapshot_sha256
        and len(authority_checks) == len(report.coverage_gaps)
        and obligation_gate["status"] == "succeeded"
        and four_quadrant_gate["status"] == "succeeded"
        and len(authority_runtime_replay["probe_results"]) == len(claim_gate["probes"])
        and all(
            item["status"] == probe["expected_status"]
            for item, probe in zip(
                authority_runtime_replay["probe_results"], claim_gate["probes"]
            )
        )
        and all(
            item["case_time"]["without_decisive_evidence"] == "not_evaluable"
            for item in authority_checks.values()
        )
    )
    return {
        "schema_version": 1,
        "project_id": "client_search",
        "role": "judge",
        "status": "succeeded" if succeeded else "failed",
        "observed_asset_ids": sorted({
            "judge_business_contract",
            "judge_investigation",
            "candidate_role",
        }),
        "checks": {
            "business_contract_loaded": bool(business_contract),
            "authority_snapshot_sha256": snapshot_sha256,
            "report": {
                "report_id": report.report_id,
                "materials": len(report.materials),
                "coverage_gaps": len(report.coverage_gaps),
            },
            "authority_runtime_replay": authority_runtime_replay,
            "judge_obligation_gate": obligation_gate,
            "four_quadrant_gate": four_quadrant_gate,
            "claim_gate": {
                "claims_sha256": claim_gate["claims_sha256"],
                "claim_count": claim_gate["claim_count"],
                "subject_count": claim_gate["subject_count"],
                "conflict_count": claim_gate["conflict_count"],
                "probes": claim_gate["probes"],
            },
            "authorities": authority_checks,
        },
    }


def main() -> int:
    payload = build_probe_payload()
    output = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).with_name("judge-solidify-smoke.json")
    )
    write_solidify_probe_result(output, payload)
    return 0 if payload["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
