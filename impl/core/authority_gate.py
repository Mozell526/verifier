"""Core 后处理：Judge assessment 的 authority.resolve 引用校验（authority.md §8）。

调用方消费规则：
- Judge LLM 在依赖某次 Authority 的 FulfillmentAssessment 中填写
  `authority_tool_call_ids`；
- Core 后处理校验引用存在且属于当前 trace：
  - 引用不存在 → 该 assessment 标 needs_human_review（不静默放行）；
  - 引用的 resolution 为 unresolved 类（unresolved/ungoverned/gap_only，
    含 claim 担保模式四值）→ not_evaluable，并把 resolution 的 EvidenceRef
    与原因挂入 assessment 的 evidence 链（grill/authority.md §2.2 与主协议
    §8.4 同口径）；
  - resolution 为 contradicted 且 assessment 为肯定性（fulfilled）→ 肯定性
    verdict 不得成立，降 not_evaluable 并标 needs_human_review（§4.2-2）；
  - resolution 为 resolved/supported → 不覆盖（Judge 已使用 statement 与
    basis 继续评价）。

Authority 不单独参与 overall 聚合；它先影响对应 FulfillmentAssessment.status，
再由现有 blocking expectation 规则确定性聚合。
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from impl.core.schema import FulfillmentAssessment, JudgeResult

NOT_EVALUABLE = "not_evaluable"

# §8.4 硬校验的成因识别：Judge 必须在 actual_evidence 中显式输出
# 「结论类型：职责外 / 依据不充分 / 输入坏 / 完全无关」（authority.md §5/§8.3、
# fulfilled.md §2.3），gate 只消费显式标记，不做自由文本关键词猜测——
# 关键词表会误伤（普通叙述里出现"无法确认"等词）或漏判，属于规则化反模式。
# 口径无担保/口径分歧是 e 路成因（judge.md §6）：由期望的 interpretations 结构
# 与 interpretation_gate 担保，不需要 authority 审计记录，故归入豁免类。
_NE_EXEMPT_CAUSE_TAGS = (
    "结论类型：输入坏",
    "结论类型：完全无关",
    "结论类型：口径无担保",
    "结论类型：口径分歧",
)
_NE_TRIGGER_CAUSE_TAGS = (
    "结论类型：职责外",
    "结论类型：依据不充分",
    "结论类型：Authority 能力不可用",
)

_NE_CAUSE_EXEMPT = "exempt"
_NE_CAUSE_REQUIRES_AUTHORITY = "requires_authority"
_NE_CAUSE_MISSING = "missing"

# 消费到这类 resolution 时，not_evaluable 的成因可由 authority 审计确定性派生，
# 不需要 judge 再复述「结论类型：」标记（gate 只要求显式成因，不要求重复）。
_NE_CAUSE_FROM_RESOLUTION_STATUSES = frozenset(
    {"unresolved", "ungoverned", "gap_only", "contradicted"}
)


def _derive_not_evaluable_cause_from_audit(
    call_ids: Sequence[str],
    tool_audit: Mapping[str, Mapping[str, Any]],
) -> str:
    """judge 判 not_evaluable 但未写显式标记时，从已消费的 authority resolution 派生。

    §8.4 硬校验的目的是防止静默放行，不要求 judge 复述权威审计已记录的成因：
    - tool_failure → Authority 能力不可用（requires_authority）；
    - unresolved/ungoverned/gap_only/contradicted → 依据不充分/资料冲突
      （requires_authority）；
    - 全部 resolved/supported → authority 已给出确定性裁决，judge 仍判
      not_evaluable 属于消费决定，成因无法从审计派生 → 保持 missing（人审）。
    """
    derived = ""
    for call_id in call_ids:
        entry = tool_audit.get(str(call_id))
        if entry is None:
            return ""
        if entry.get("tool_failure"):
            return _NE_CAUSE_REQUIRES_AUTHORITY
        resolution = entry.get("resolution")
        if resolution is None:
            continue
        status = str(getattr(resolution, "status", "") or "").strip()
        if status in _NE_CAUSE_FROM_RESOLUTION_STATUSES:
            return _NE_CAUSE_REQUIRES_AUTHORITY
    return derived

# claim 担保模式四值中的 unresolved 类（grill/authority.md §2.2）：与提问模式
# unresolved 同口径，必须强制把依赖该断言的 assessment 降为 not_evaluable。
_UNRESOLVED_RESOLUTION_STATUSES = frozenset({"unresolved", "ungoverned", "gap_only"})


def _assessment_evidence_text(assessment: FulfillmentAssessment) -> str:
    parts: list[str] = []
    for key in ("actual_evidence", "expected_evidence"):
        for entry in list(getattr(assessment, key, None) or []):
            if isinstance(entry, str):
                parts.append(entry)
            elif isinstance(entry, dict):
                for sub in ("summary", "value", "reason", "text"):
                    value = entry.get(sub)
                    if value:
                        parts.append(str(value))
    if getattr(assessment, "downstream_impact", ""):
        parts.append(str(assessment.downstream_impact))
    return " ".join(parts)


def _classify_not_evaluable_cause(assessment: FulfillmentAssessment) -> str:
    """§8.4：分类 not_evaluable 的显式成因，不根据自由文本猜测。

    只认 Judge 显式输出的「结论类型：」标记。无标记或未知标记时返回 missing，
    由调用方 fail-closed 标记人审；不能把未知成因直接猜成职责外/依据不充分，
    也不能静默放行。
    """
    text = _assessment_evidence_text(assessment)
    if any(tag in text for tag in _NE_EXEMPT_CAUSE_TAGS):
        return _NE_CAUSE_EXEMPT
    if any(tag in text for tag in _NE_TRIGGER_CAUSE_TAGS):
        return _NE_CAUSE_REQUIRES_AUTHORITY
    return _NE_CAUSE_MISSING


def _append_evidence(assessment: FulfillmentAssessment, entry: Mapping[str, Any]) -> None:
    current = list(assessment.evidence_refs or [])
    current.append(dict(entry))
    assessment.evidence_refs = current


def _looks_like_resolution_id(call_id: str) -> bool:
    """识别疑似"决议编号/audit_ref"而非真实 tool_call_id 的引用（仅用于诊断提示）。

    真实调用 id 形如 authority.<project>.<hex12>；纯数字（旧行为编造的决议编号）
    或 resolution.N@<hash12>（未注入的 audit_ref）都是不可审计引用。
    """
    return bool(re.fullmatch(r"resolution\.\d+@[0-9a-f]{12}", call_id)) or bool(
        re.fullmatch(r"\d+", call_id)
    )


# §8.3 resolved 能力/职责边界结论的 statement 前缀（authority.md §5/§8.2）：
# 能力/职责边界问题的 statement 必须以「职责外：」「职责内能力缺失：」「职责内正常：」
# 开头（authority prompt 硬格式要求），gate 据此确定性消费。
_BOUNDARY_OUTSIDE_PREFIX = "职责外"
_CAPABILITY_GAP_PREFIX = "职责内能力缺失"
_WITHIN_SCOPE_PREFIX = "职责内正常"
_CONCLUSION_PREFIXES = (
    (_BOUNDARY_OUTSIDE_PREFIX, "boundary_outside"),
    (_CAPABILITY_GAP_PREFIX, "capability_gap"),
    (_WITHIN_SCOPE_PREFIX, "within_scope"),
)


def _conclusion_kind_from_statement(statement: str) -> str:
    text = str(statement or "").strip()
    for prefix, kind in _CONCLUSION_PREFIXES:
        if text.startswith(prefix):
            return kind
    return ""


def _scan_authority_calls(
    call_ids: Sequence[str],
    tool_audit: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """预扫描一个 assessment 引用的所有调用，收集 §8.3 确定性消费所需信号。

    只读不改状态：reference_error（引用不存在）、tool_failure、unresolved 类调用、
    supported/resolved 的结论类型（职责外/职责内能力缺失/职责内正常）。
    """
    kinds: set[str] = set()
    has_unresolved = False
    has_tool_failure = False
    has_reference_error = False
    for call_id in call_ids:
        entry = tool_audit.get(str(call_id))
        if entry is None:
            has_reference_error = True
            continue
        if entry.get("tool_failure"):
            has_tool_failure = True
            continue
        resolution = entry.get("resolution")
        if resolution is None:
            continue
        status = str(getattr(resolution, "status", "") or "").strip()
        if status in _UNRESOLVED_RESOLUTION_STATUSES:
            has_unresolved = True
            continue
        if status in {"resolved", "supported"}:
            kind = _conclusion_kind_from_statement(
                str(getattr(resolution, "statement", "") or "")
            )
            if kind:
                kinds.add(kind)
    return {
        "conclusion_kinds": kinds,
        "has_unresolved": has_unresolved,
        "has_tool_failure": has_tool_failure,
        "has_reference_error": has_reference_error,
    }


def apply_authority_gate(
    result: JudgeResult,
    tool_audit: Mapping[str, Mapping[str, Any]],
) -> JudgeResult:
    """按当前 trace 的 authority.resolve Tool audit 校验每个 assessment 的引用。

    tool_audit: tool_call_id -> {"request": AuthorityRequest,
                                 "resolution": AuthorityResolution,
                                 "environment_snapshot_sha256": str}
    只接受当前 trace 内的调用；audit 之外的引用一律视为不存在。
    """
    if not result.fulfillment_assessments:
        return result
    changed = False
    for assessment in result.fulfillment_assessments:
        call_ids = list(assessment.authority_tool_call_ids or [])
        scanned = _scan_authority_calls(call_ids, tool_audit)
        kinds = scanned["conclusion_kinds"]
        # §8.3 确定性消费（fulfilled.md §3 第二步）：先于 ne_cause/显式标记处理，
        # 避免 judge 自由消费与「结论类型：」标记机制互相矛盾。
        if "boundary_outside" in kinds:
            # 职责外（已确认产品没有该能力）→ 说不清（not_evaluable），
            # 无论 judge 判 fulfilled/not_fulfilled/not_evaluable 都确定性落位。
            if assessment.status != NOT_EVALUABLE:
                assessment.status = NOT_EVALUABLE
                changed = True
            _append_evidence(assessment, {
                "kind": "authority_boundary_outside",
                "reason": (
                    "authority 已裁决该能力/职责边界为「职责外」（产品没有该能力/"
                    "不在职责范围）；按 fulfilled.md §2.3 判说不清（not_evaluable），"
                    "不因如实拒绝/未编造而判办成（fulfilled.md §5）。"
                ),
                "basis_evidence_ref_ids": [
                    item
                    for call_id in call_ids
                    for item in (
                        list(
                            getattr(
                                (tool_audit.get(str(call_id)) or {}).get("resolution")
                                or {},
                                "basis_evidence_ref_ids",
                                (),
                            )
                        )
                        if (tool_audit.get(str(call_id)) or {}).get("resolution")
                        else []
                    )
                ],
                "environment_snapshot_sha256": str(
                    (tool_audit.get(str(call_ids[0])) or {}).get(
                        "environment_snapshot_sha256"
                    )
                    or ""
                ),
            })
            ne_cause = _NE_CAUSE_REQUIRES_AUTHORITY
            changed = True
        elif (
            "capability_gap" in kinds
            and assessment.status == NOT_EVALUABLE
            and not scanned["has_unresolved"]
            and not scanned["has_tool_failure"]
            and not scanned["has_reference_error"]
        ):
            # 职责内能力缺失（应具备但未实现/表达不了）→ 不得降为 not_evaluable：
            # 功能未实现=没办成（fulfilled.md §2.2/§4.1，authority.md §8.3）。
            assessment.status = "not_fulfilled"
            _append_evidence(assessment, {
                "kind": "authority_capability_gap",
                "reason": (
                    "authority 已裁决该能力/职责边界为「职责内能力缺失」（应具备但"
                    "未实现/表达不了）；功能未实现=没办成，不能降级为说不清"
                    "（fulfilled.md §2.2/§4.1，authority.md §8.3）。"
                ),
            })
            ne_cause = ""
            changed = True
        else:
            ne_cause = (
                _classify_not_evaluable_cause(assessment)
                if assessment.status == NOT_EVALUABLE
                else ""
            )
        if ne_cause == _NE_CAUSE_MISSING and call_ids:
            # judge 未写「结论类型：」标记，但已消费 authority resolution：
            # 成因从审计确定性派生（不要求 judge 复述权威证据）。
            derived = _derive_not_evaluable_cause_from_audit(call_ids, tool_audit)
            if derived:
                ne_cause = derived
        if ne_cause == _NE_CAUSE_MISSING:
            _append_evidence(assessment, {
                "kind": "not_evaluable_cause_missing",
                "needs_human_review": True,
                "reason": (
                    "assessment 判定 not_evaluable，但没有在 evidence 中使用受支持的"
                    "“结论类型：职责外/完全无关/依据不充分/输入坏/Authority 能力不可用”"
                    "显式说明成因；fulfilled.md §2.3 要求说清差在哪儿，不能静默放行"
                ),
            })
            changed = True
        if not call_ids:
            # §8.4 硬校验：not_evaluable 且成因需要 Authority 审计，但没有
            # authority.resolve 调用记录 → needs_human_review，不静默放行。
            if ne_cause == _NE_CAUSE_REQUIRES_AUTHORITY:
                _append_evidence(assessment, {
                    "kind": "authority_required_not_consulted",
                    "needs_human_review": True,
                    "cause": "职责外、依据不充分或 Authority 能力不可用",
                    "reason": (
                        "assessment 判定 not_evaluable 且成因需要 Authority 审计记录，"
                        "但没有 authority.resolve 调用记录；这类结论必须有 Authority "
                        "真实查证的调用记录（没查证 ≠ 查不了），不能静默放行"
                        "（authority.md §8.4 / fulfilled.md §2.3）"
                    ),
                })
                changed = True
            continue
        for call_id in call_ids:
            entry = tool_audit.get(str(call_id))
            if entry is None:
                # 引用不存在 → needs_human_review，不静默放行
                assessment.status = NOT_EVALUABLE
                hint = ""
                if _looks_like_resolution_id(str(call_id)):
                    hint = (
                        "；该 id 形如决议编号/audit_ref，但当前 trace 未注入对应"
                        "决议复用记录或现场调用，可能为旧版决议、伪造引用或"
                        "audit_ref 拼写错误（数字 id 不是合法引用）"
                    )
                _append_evidence(assessment, {
                    "kind": "authority_reference_missing",
                    "tool_call_id": str(call_id),
                    "needs_human_review": True,
                    "reason": "assessment references an authority.resolve tool call that is absent from the current trace audit" + hint,
                })
                changed = True
                continue
            if entry.get("tool_failure"):
                # §8.4：Tool / Agent 执行失败（能力不可用）→ not_evaluable，
                # 原因必须写"Authority 能力不可用"，不能伪写成资料冲突。
                # 与"真查证过仍 unresolved"区分开：这是工具/宿主执行失败，
                # 不是业务裁决结果，也不标 needs_human_review（不是静默放行）。
                assessment.status = NOT_EVALUABLE
                _append_evidence(assessment, {
                    "kind": "authority_tool_failure",
                    "tool_call_id": str(call_id),
                    "reason": "Authority 能力不可用："
                    + str(entry.get("error") or "工具执行失败"),
                    "environment_snapshot_sha256": str(
                        entry.get("environment_snapshot_sha256") or ""
                    ),
                })
                changed = True
                continue
            resolution = entry.get("resolution")
            if resolution is None:
                assessment.status = NOT_EVALUABLE
                _append_evidence(assessment, {
                    "kind": "authority_audit_missing_resolution",
                    "tool_call_id": str(call_id),
                    "needs_human_review": True,
                })
                changed = True
                continue
            resolution_status = str(
                getattr(resolution, "status", "") or ""
            ).strip()
            if resolution_status in _UNRESOLVED_RESOLUTION_STATUSES:
                # unresolved 类（含 claim 模式 ungoverned/gap_only）→ 该 assessment
                # 无法评价；blocking 由现有聚合规则决定（grill/authority.md §2.2）
                assessment.status = NOT_EVALUABLE
                _append_evidence(assessment, {
                    "kind": "authority_unresolved",
                    "tool_call_id": str(call_id),
                    "resolution_status": resolution_status,
                    "reason": str(getattr(resolution, "reason", "") or ""),
                    "basis_evidence_ref_ids": list(
                        getattr(resolution, "basis_evidence_ref_ids", ()) or ()
                    ),
                    "required_evidence": list(
                        getattr(resolution, "required_evidence", ()) or ()
                    ),
                    "environment_snapshot_sha256": str(
                        entry.get("environment_snapshot_sha256") or ""
                    ),
                })
                changed = True
            elif resolution_status == "contradicted" and assessment.status == "fulfilled":
                # §4.2-2：contradicted 的肯定性 verdict 不得成立，标人审
                assessment.status = NOT_EVALUABLE
                _append_evidence(assessment, {
                    "kind": "authority_contradicted",
                    "tool_call_id": str(call_id),
                    "needs_human_review": True,
                    "reason": (
                        "resolution 为 contradicted：依赖该断言的肯定性结论不得成立，"
                        "转人工复核（spec/grill/authority.md §4.2-2）。"
                    ),
                    "basis_evidence_ref_ids": list(
                        getattr(resolution, "basis_evidence_ref_ids", ()) or ()
                    ),
                    "environment_snapshot_sha256": str(
                        entry.get("environment_snapshot_sha256") or ""
                    ),
                })
                changed = True
            # resolved/supported → 不覆盖：Judge 已用 statement 与 basis 继续原有评价
    if changed:
        from impl.core.schema.normalize import normalize_fulfillment_assessment

        result.fulfillment_assessments = [
            normalize_fulfillment_assessment(item) or item
            for item in result.fulfillment_assessments
        ]
    return result
