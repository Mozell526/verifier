"""e 路口径 gate（judge.md §6）：期望字面闭合的输出义务，Core 确定性后处理。

期望默认字面闭合（e 默认无戳记）：expectation 不带 interpretations 时本 gate
不做任何事，字面对账路径零改动。仅当 judge（当前仍是单次 LLM 调用里的隐式 e+C）
给某条 expectation 附加了超出诉求字面的口径（派生解释）时，输出义务生效：

- 口径必须带担保（warrant：cite 进 z——项目文档 / 受治理规则 key / 调查产物 /
  authority.resolve 调用 id）。给不出担保 → 强制 说不清（口径无担保）+ 缺料清单，
  不许用常识补齐（judge.md §6）。
- 有担保口径彼此冲突、读法分歧材料定夺不了（e 侧装配时显式标 divergent）→
  强制 说不清（口径分歧），不许静默择一（judge.md §1 成因穷尽、§6）。
- 有担保且无分歧的口径不被本 gate 否决：口径是拿来消费的，不是拿来加戳的。
  戳记三件套只构成 G——本 gate 不给期望造第二个 G（judge.md §6）。

对齐 authority_gate 的反关键词原则：只消费结构字段（interpretations），
不做自由文本猜测。工具 / provider 失败不经此 gate——那是本次运行 error
（judge.md §7.7），不得伪装成业务"说不清"。
"""
from __future__ import annotations

from typing import Any, Mapping

from impl.core.schema import JudgeResult

NOT_EVALUABLE = "not_evaluable"

# 说不清成因标签（judge.md §6）：与 authority_gate §8.4 的「结论类型：」
# 显式标记同一消费机制（authority_gate 把这两个标签列为豁免——e 路成因由
# 本 gate 结构化担保，不需要 authority 审计记录）。
INTERPRETATION_UNWARRANTED_TAG = "结论类型：口径无担保"
INTERPRETATION_DIVERGENCE_TAG = "结论类型：口径分歧"

_GATE_KINDS = frozenset({"interpretation_unwarranted", "interpretation_divergence"})


def _interpretation_entries(expectation: Any) -> list[dict[str, Any]]:
    raw = getattr(expectation, "interpretations", None) or []
    entries: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, Mapping):
            entries.append(dict(item))
        elif str(item or "").strip():
            # 裸字符串口径按无担保收敛（fail-closed），不静默丢弃。
            entries.append({"statement": str(item)})
    return entries


def _already_gated(assessment: Any) -> bool:
    for entry in assessment.evidence_refs or []:
        if isinstance(entry, Mapping) and str(entry.get("kind") or "") in _GATE_KINDS:
            return True
    return False


def apply_interpretation_gate(result: JudgeResult) -> JudgeResult:
    """按 expectation.interpretations 结构强制执行口径输出义务（幂等）。

    在 finalize_judge_result 的 overall 派生之前运行，被强制的 not_evaluable
    参与 blocking 聚合；判后派生约束不变——本 gate 只降级 assessment，
    永不改写字面对账结论以外的任何东西，也不制造 fulfilled。
    """
    expectations = list(result.business_expectations or [])
    if not expectations:
        return result
    assessments = {
        str(getattr(item, "expectation_id", "") or ""): item
        for item in (result.fulfillment_assessments or [])
    }
    for expectation in expectations:
        entries = _interpretation_entries(expectation)
        if not entries:
            continue  # 字面闭合路径：零改动
        divergent = [item for item in entries if item.get("divergent")]
        unwarranted = [
            item for item in entries if not str(item.get("warrant") or "").strip()
        ]
        if not divergent and not unwarranted:
            continue  # 全部有担保且无分歧：口径被消费，不否决
        assessment = assessments.get(
            str(getattr(expectation, "expectation_id", "") or "")
        )
        if assessment is None:
            continue  # 缺 assessment 由 _judge_self_check 负责，不在这里补造
        if _already_gated(assessment):
            continue
        if divergent:
            tag = INTERPRETATION_DIVERGENCE_TAG
            kind = "interpretation_divergence"
            missing = [
                "能定夺以下读法分歧的受治理口径/担保材料："
                + "；".join(str(item.get("statement") or "") for item in divergent)
            ]
            reason = (
                "期望附带的口径存在读法分歧（有担保口径冲突或材料定夺不了），"
                "不得静默择一，强制 说不清（口径分歧）（judge.md §1/§6）"
            )
        else:
            tag = INTERPRETATION_UNWARRANTED_TAG
            kind = "interpretation_unwarranted"
            missing = [
                f"为口径「{str(item.get('statement') or '')}」背书的担保材料"
                "（项目文档/受治理规则/调查产物/authority 裁决）"
                for item in unwarranted
            ]
            reason = (
                "期望附带超出诉求字面的口径但给不出担保（warrant 为空），"
                "不得用常识补齐，强制 说不清（口径无担保）（judge.md §6）"
            )
        assessment.status = NOT_EVALUABLE
        evidence_line = f"{tag} · 缺料清单：{'；'.join(missing)}"
        actual = list(assessment.actual_evidence or [])
        if evidence_line not in actual:
            actual.append(evidence_line)
        assessment.actual_evidence = actual
        refs = list(assessment.evidence_refs or [])
        refs.append({
            "kind": kind,
            "cause": tag,
            "reason": reason,
            "interpretations": entries,
            "missing_material": missing,
        })
        assessment.evidence_refs = refs
    return result
