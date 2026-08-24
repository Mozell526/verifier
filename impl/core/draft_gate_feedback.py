"""Harness-facing feedback for recoverable Draft gate failures.

This is control-plane guidance for the AI editing Investigation/Solidify assets.
It is intentionally separate from Judge Runtime schemas and business outcomes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from impl.core.portable_artifact import (
    project_artifact_repository_root,
    write_active_artifact,
    write_portable_export,
)

FEEDBACK_SCHEMA_VERSION = 1


def build_authority_gate_feedback(
    *,
    project_id: str,
    role: str,
    owner_stage: str,
    error: BaseException | str,
    affected_subjects: Sequence[str] = (),
) -> dict[str, Any]:
    message = str(error).strip() or type(error).__name__
    lowered = message.casefold()
    gate_id = "AUTHORITY_GATE"
    diagnosis_code = "authority_gate_failed"
    diagnosis = (
        "Draft Authority 门禁失败；当前产物没有证明 Authority 调查资产已被正确生成并固化。"
    )
    missing_proof: list[str] = [message]
    improvements: list[str] = []
    prohibited = [
        "不得修改冻结 Case、expected_status 或 Production Judge 来迎合门禁",
        "不得把 SearchHit 或手工构造的 AuthorityResolution 冒充决定性 Runtime 证据",
    ]
    pass_condition = "修复责任阶段后重新运行同一 Authority 门禁并通过。"

    if "content hash changed" in lowered or "source revision" in lowered:
        owner_stage = "investigate"
        gate_id = "AUTHORITY_MATERIAL_FRESHNESS"
        diagnosis_code = "authority_material_stale"
        diagnosis = (
            "Authority 调查依赖的业务资料 revision/hash 已变化，当前调查结论和 Claim Index "
            "不能证明仍对应真实资料。"
        )
        improvements = [
            "重新 Load 发生变化的原始资料并检查 Authority claim、条件和 coverage gap 是否仍成立",
            "完成重查后更新 EvidenceRef revision/hash，并重新生成 Investigation validation receipt",
        ]
        pass_condition = "所有 Authority 决定资料与当前 revision/hash 一致，Claim/Gap 重新校验通过。"
    elif "authority runtime replay" in lowered or "real authority.resolve" in lowered:
        gate_id = "AUTHORITY_RUNTIME_REPLAY"
        diagnosis_code = "authority_runtime_not_proven"
        diagnosis = (
            "Investigation 已提供 Authority Claim/Probe，但 Solidify 没有证明正式 authority.resolve "
            "能通过 Runtime Search→Load 消费这些资产；当前 smoke 仍不足以证明 Authority 已接通。"
        )
        improvements = [
            "使用冻结 Probe 的完整 decision question 调用正式 authority.resolve",
            "保留真实 tool_call_id、Tool audit、Environment snapshot 和 Evidence Load 记录",
            "比较实际 status、basis_evidence_ref_ids、required_evidence 与冻结 Probe",
            "若资料不可 Search/Load，修复 ContextUnit、Key-Index 或 Authority Tool 映射",
        ]
        prohibited.extend([
            "不得在 Probe 请求中注入 expected_status",
            "不得只测试 apply_authority_gate 对手工 Resolution 的处理",
        ])
        pass_condition = (
            "至少一条 resolved 和一条 unresolved Probe 经正式 authority.resolve 重放，"
            "并具有可验证 Tool audit 和 Load 证据。"
        )
    elif (
        "solidify" in lowered
        or "mapping" in lowered
        or "runtime observable" in lowered
        or "unknown contract source id" in lowered
    ):
        owner_stage = "solidify"
        gate_id = "AUTHORITY_SOLIDIFY_MAPPING"
        diagnosis_code = "authority_assets_not_solidified"
        diagnosis = (
            "Authority 调查资产尚未完整映射或被 Runtime observable 证明，Solidify 不能进入 Draft Loop。"
        )
        improvements = [
            "检查 Authority report、Claim Index、CoverageGap 和 Search→Load 能力的 Solidify mapping",
            "让 runtime observable 覆盖实际承载这些能力的 Investigation/Context/Tool 资产",
        ]
        pass_condition = "所有必需 Authority source ID 均有资产映射和成功的 Runtime observable。"
    elif any(token in lowered for token in (
        "claim conflict",
        "coveragegap",
        "coverage gap",
        "decisive evidenceref",
        "bindings for unknown subjects",
    )):
        owner_stage = "investigate"
        gate_id = "AUTHORITY_INVESTIGATION_CLAIMS"
        diagnosis_code = "authority_claim_space_invalid"
        diagnosis = (
            "Authority 调查的 Claim/冲突/缺口空间不完整，Harness 目前无法判断哪些结论可直接采用、"
            "哪些必须交给 Authority 现场裁决。"
        )
        improvements = [
            "检查受影响 Subject 的来源 Claim、适用条件和 EvidenceRef 是否真实可 Load",
            "用决定性资料登记 Resolution；无法裁决时登记具体 CoverageGap 和 required_evidence",
            "重新生成并校验冻结 Authority Probe",
        ]
        pass_condition = "每个冲突或潜在冲突 Subject 都有可追溯 Resolution 或具体 CoverageGap。"

    return {
        "schema_version": FEEDBACK_SCHEMA_VERSION,
        "project_id": project_id,
        "role": role,
        "authority_problem": True,
        "owner_stage": owner_stage,
        "gate": gate_id,
        "diagnosis_code": diagnosis_code,
        "diagnosis": diagnosis,
        "affected_subjects": sorted({str(item) for item in affected_subjects if str(item).strip()}),
        "missing_proof": missing_proof,
        "improvement_options": improvements,
        "prohibited_shortcuts": prohibited,
        "pass_condition": pass_condition,
    }



def analyze_judge_gate_obligations(
    *,
    result: Mapping[str, Any],
    runtime: Mapping[str, Any] | None = None,
    obligations: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Evaluate Harness-authored obligations against one final Judge side.

    The gate deliberately does not infer business semantics from case text.  The
    Harness/Loop reviewer identifies transient trigger types from the frozen
    trace; this function only verifies observable final-model behaviour:
    expectation topology, real authority calls, audit outcome consumption and
    overall aggregation.  This keeps the gate generic and prevents case-keyword
    rules from leaking into Runtime.
    """
    runtime = dict(runtime or {})
    expectations = {
        str(item.get("expectation_id") or ""): dict(item)
        for item in (result.get("business_expectations") or [])
        if isinstance(item, Mapping) and str(item.get("expectation_id") or "")
    }
    assessments = {
        str(item.get("expectation_id") or ""): dict(item)
        for item in (result.get("fulfillment_assessments") or [])
        if isinstance(item, Mapping) and str(item.get("expectation_id") or "")
    }
    audit = runtime.get("authority_audit") or {}
    if not isinstance(audit, Mapping):
        audit = {}
    observed_calls = {str(item) for item in (runtime.get("authority_tool_call_ids") or [])}
    for assessment in assessments.values():
        observed_calls.update(str(item) for item in (assessment.get("authority_tool_call_ids") or []))

    findings: list[dict[str, Any]] = []
    assessment_actions: list[dict[str, Any]] = []
    checked_claims: list[dict[str, Any]] = []
    missing_assessments = sorted(set(expectations) - set(assessments))
    if missing_assessments:
        findings.append({
            "kind": "expectation_topology",
            "code": "assessment_missing",
            "expectation_ids": missing_assessments,
            "owner": "candidate_judge_output",
            "required_change": "为每个 business expectation 生成同 ID assessment。",
        })

    blocking_ids = {eid for eid, item in expectations.items() if bool(item.get("blocking"))}
    if expectations and not blocking_ids:
        findings.append({
            "kind": "expectation_topology",
            "code": "blocking_core_missing",
            "expectation_ids": sorted(expectations),
            "owner": "candidate_judge_expectation_construction",
            "required_change": "先派生用户核心交付并标记 blocking；安全/透明处理不能替代核心交付。",
        })

    for obligation in obligations:
        subject = str(obligation.get("subject") or obligation.get("trigger") or "authority-obligation")
        trigger = str(obligation.get("trigger") or "unspecified")
        dependent_ids = [
            str(item) for item in (obligation.get("blocking_expectation_ids") or []) if str(item)
        ]
        required = bool(obligation.get("authority_required"))
        relevant_calls: set[str] = set()
        for eid in dependent_ids:
            relevant_calls.update(
                str(item) for item in (assessments.get(eid, {}).get("authority_tool_call_ids") or [])
            )
        if required and not relevant_calls and bool(obligation.get("compact_material_backed")):
            checked_claims.append({
                "subject": subject,
                "expectation_ids": dependent_ids,
                "support": "compact_material",
            })
            continue
        if required and not relevant_calls:
            # 归责优先级：全量资料存在但压缩投影缺失 > authority 未构造/不可用
            # > 工具已构造但 Judge 未调用。没有这些可验证元数据时，保留旧的
            # not_called 兼容口径，避免把未知误罚成 Judge 责任。
            full_material = bool(obligation.get("full_material_governs"))
            compact_visible = obligation.get("compact_projection_visible")
            authority_available = obligation.get("authority_availability") in {"available", True}
            if full_material and compact_visible is False:
                code = "compaction_miss"
                owner = "solidify_compaction_projection"
                target = "补齐压缩 ContextUnit/manifest 到该 MaterialDecision 的可追溯投影，并保留 source_ref_id。"
            elif not authority_available and obligation.get("authority_availability") in {"unavailable", False}:
                code = "availability_miss"
                owner = "investigate_authority_availability"
                target = "补充或修复 Authority Search→Load 能力；工具不可用时不得把该 finding 计为 Judge 误用。"
            else:
                code = "not_called"
                owner = str(obligation.get("owner") or "candidate_judge_trigger_logic")
                target = "让该通用 trigger 提供并调用 authority.resolve；未裁决时依赖项不得给肯定结论。"
            finding_type = {
                    "not_called": "judge_failed_to_call",
                    "availability_miss": "availability_miss",
                    "compaction_miss": "compaction_miss",
                }.get(code, code)
            findings.append({
                "kind": "authority_obligation",
                "finding_type": finding_type,
                "code": code,
                "subject": subject,
                "trigger": trigger,
                "expectation_ids": dependent_ids,
                "observed_call_ids": [],
                "owner": owner,
                "remediation_target": target,
                "required_change": target,
            })
            checked_claims.append({
                "subject": subject,
                "expectation_ids": dependent_ids,
                "support": "missing",
                "finding_type": finding_type,
            })
            if finding_type == "judge_failed_to_call":
                for eid in dependent_ids:
                    assessment_actions.append({
                        "assessment_id": eid,
                        "action": "downgrade_to_not_evaluable",
                        "reason": "normative claim was used without compact-material or Authority backing",
                    })
            continue
        for call_id in sorted(relevant_calls):
            entry = audit.get(call_id) if isinstance(audit, Mapping) else None
            if not isinstance(entry, Mapping):
                findings.append({
                    "kind": "authority_obligation",
                    "code": "audit_missing",
                    "subject": subject,
                    "trigger": trigger,
                    "expectation_ids": dependent_ids,
                    "observed_call_ids": [call_id],
                    "owner": "solidify_runtime_observability",
                    "required_change": "保留真实 authority Tool audit；assessment 引用不能脱离当前 trace audit。",
                })
                continue
            resolution = entry.get("resolution") or {}
            status = str(resolution.get("status") or "") if isinstance(resolution, Mapping) else ""
            tool_failure = bool(entry.get("tool_failure"))
            checked_claims.append({
                "subject": subject,
                "expectation_ids": dependent_ids,
                "tool_call_id": call_id,
                "support": "tool_failure" if tool_failure else status or "missing_resolution",
            })
            dependent_statuses = {
                str(assessments.get(eid, {}).get("status") or "") for eid in dependent_ids
            }
            if tool_failure:
                findings.append({
                    "kind": "authority_obligation",
                    "code": "tool_failure",
                    "subject": subject,
                    "trigger": trigger,
                    "expectation_ids": dependent_ids,
                    "observed_call_ids": [call_id],
                    "owner": "solidify_authority_tool",
                    "required_change": "修复 authority.resolve 结构化输出/调用稳定性；该 side 不得作为肯定改善证据。",
                })
            elif (
                status in {"unresolved", "ungoverned", "gap_only"}
                and any(item not in {"not_evaluable", ""} for item in dependent_statuses)
            ) or (
                status == "contradicted"
                and "fulfilled" in dependent_statuses
            ):
                action = "require_human_review" if status == "contradicted" else "downgrade_to_not_evaluable"
                for eid in dependent_ids:
                    dependent_status = str(
                        assessments.get(eid, {}).get("status") or ""
                    )
                    if (
                        status == "contradicted"
                        and dependent_status != "fulfilled"
                    ) or dependent_status in {"not_evaluable", ""}:
                        continue
                    if dependent_status:
                        assessment_actions.append({
                            "assessment_id": eid,
                            "action": action,
                            "reason": f"authority status {status} cannot support the affirmative assessment",
                            "tool_call_id": call_id,
                        })
                findings.append({
                    "kind": "authority_obligation",
                    "finding_type": "authority_status_misconsumed",
                    "code": "misconsumed",
                    "subject": subject,
                    "trigger": trigger,
                    "expectation_ids": dependent_ids,
                    "observed_call_ids": [call_id],
                    "owner": "candidate_judge_authority_consumption",
                    "remediation_target": "按 Authority 四值消费：ungoverned/gap_only/unresolved 的依赖项降为 not_evaluable；contradicted 不得支撑肯定结论。",
                    "required_change": "按 Authority 四值消费：ungoverned/gap_only/unresolved 的依赖项降为 not_evaluable；contradicted 不得支撑肯定结论。",
                })

    for obligation in obligations:
        for eid in obligation.get("expected_non_blocking_expectation_ids") or []:
            eid = str(eid)
            if eid in expectations and bool(expectations[eid].get("blocking")):
                findings.append({
                    "kind": "expectation_topology",
                    "code": "safety_expectation_marked_blocking",
                    "expectation_ids": [eid],
                    "owner": "candidate_judge_expectation_construction",
                    "required_change": "将安全拒绝、透明说明或不编造条件保留为独立 non-blocking 验收项。",
                })

    counts: dict[str, int] = {}
    for finding in findings:
        code = str(finding.get("code") or "unknown")
        counts[code] = counts.get(code, 0) + 1
    return {
        "schema_version": 1,
        "status": "passed" if not findings else "failed",
        "authority_obligations": len(obligations),
        "observed_authority_calls": sorted(observed_calls),
        "finding_counts": counts,
        "findings": findings,
        "checked_claims": checked_claims,
        "assessment_actions": assessment_actions,
    }

def render_gate_feedback(feedback: Mapping[str, Any]) -> str:
    def bullets(values: Any) -> str:
        items = [str(item) for item in values or []]
        return "\n".join(f"- {item}" for item in items) or "- 无"

    return (
        "[Draft Authority Gate Feedback]\n\n"
        f"Owner stage: {feedback.get('owner_stage')}\n"
        f"Gate: {feedback.get('gate')}\n"
        f"Diagnosis code: {feedback.get('diagnosis_code')}\n\n"
        f"Diagnosis:\n{feedback.get('diagnosis')}\n\n"
        f"Affected subjects:\n{bullets(feedback.get('affected_subjects'))}\n\n"
        f"Missing proof:\n{bullets(feedback.get('missing_proof'))}\n\n"
        f"Improve by investigating:\n{bullets(feedback.get('improvement_options'))}\n\n"
        f"Do not optimize by:\n{bullets(feedback.get('prohibited_shortcuts'))}\n\n"
        f"Pass when:\n{feedback.get('pass_condition')}\n"
    )


def write_gate_feedback(path: Path, feedback: Mapping[str, Any]) -> Path:
    target = Path(path)
    payload = dict(feedback)
    payload["harness_prompt"] = render_gate_feedback(payload)
    repository_root = project_artifact_repository_root(target)
    if repository_root is not None:
        from impl.core.active_artifacts import DEFAULT_ACTIVE_ARTIFACT_REGISTRY

        classification = DEFAULT_ACTIVE_ARTIFACT_REGISTRY.classify_path(
            repository_root, target
        )
        if classification in {"active", "unknown_owned"}:
            write_active_artifact(
                "gate_feedback",
                target,
                payload,
                repository_root=repository_root,
            )
            return target
    write_portable_export(target, payload)
    return target


def score_judge_gate_replay(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Score a frozen, human/Harness-reviewed gate replay set.

    Only ``label_quality=closed_loop`` rows affect thresholds. Boundary rows are
    preserved for observation because references are not ground truth. A dirty
    row is detected when the gate emits at least one finding; a clean row is a
    false positive when it emits any finding. Every emitted finding must point to
    a concrete remediation target.
    """
    closed = [dict(row) for row in records if row.get("label_quality") == "closed_loop"]
    boundary = [dict(row) for row in records if row.get("label_quality") != "closed_loop"]
    dirty = [row for row in closed if row.get("expected_gate") == "dirty"]
    clean = [row for row in closed if row.get("expected_gate") == "clean"]

    def findings(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        gate = row.get("gate") or {}
        values = gate.get("findings") or [] if isinstance(gate, Mapping) else []
        return [item for item in values if isinstance(item, Mapping)]

    dirty_detected = sum(bool(findings(row)) for row in dirty)
    clean_false_positives = sum(bool(findings(row)) for row in clean)
    emitted = [item for row in closed for item in findings(row)]
    actionable = [
        item for item in emitted
        if str(item.get("remediation_target") or item.get("required_change") or "").strip()
    ]
    dirty_recall = dirty_detected / len(dirty) if dirty else 0.0
    actionable_rate = len(actionable) / len(emitted) if emitted else 1.0
    passed = bool(
        dirty
        and clean
        and dirty_recall >= 0.90
        and clean_false_positives <= 1
        and actionable_rate == 1.0
    )
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "closed_loop_count": len(closed),
        "boundary_observation_count": len(boundary),
        "dirty_count": len(dirty),
        "dirty_detected": dirty_detected,
        "dirty_recall": dirty_recall,
        "clean_count": len(clean),
        "clean_false_positives": clean_false_positives,
        "actionable_finding_rate": actionable_rate,
        "thresholds": {
            "dirty_recall_min": 0.90,
            "clean_false_positives_max": 1,
            "actionable_finding_rate": 1.0,
        },
        "boundary_case_ids": [str(row.get("case_id") or "") for row in boundary],
    }
