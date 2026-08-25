"""口径输出义务测试（judge.md §6）：e 附加超出字面的口径必须带担保，
无担保 → 说不清（口径无担保）+ 缺料清单；分歧 → 说不清（口径分歧）；
字面闭合路径零改动。不依赖 live LLM。"""
from __future__ import annotations

from impl.core.authority_gate import apply_authority_gate
from impl.core.interpretation_gate import (
    INTERPRETATION_DIVERGENCE_TAG,
    INTERPRETATION_UNWARRANTED_TAG,
    apply_interpretation_gate,
)
from impl.core.judge import finalize_judge_result
from impl.core.schema import (
    BusinessExpectation,
    FulfillmentAssessment,
    JudgeResult,
    normalize_business_expectation,
)


def _result(expectation: BusinessExpectation, status: str = "fulfilled") -> JudgeResult:
    return JudgeResult(
        trace_id="t1",
        project_id="p1",
        business_expectations=[expectation],
        fulfillment_assessments=[
            FulfillmentAssessment(expectation_id=expectation.expectation_id, status=status),
        ],
    )


def _expectation(interpretations=None) -> BusinessExpectation:
    return BusinessExpectation(
        expectation_id="核心交付",
        blocking=True,
        expected_outcome="按诉求字面交付",
        interpretations=list(interpretations or []),
    )


def test_literal_path_untouched():
    # e 默认无戳记、字面闭合：不带口径的期望，gate 零改动。
    result = _result(_expectation())
    out = apply_interpretation_gate(result)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "fulfilled"
    assert not assessment.evidence_refs
    assert not assessment.actual_evidence


def test_unwarranted_interpretation_forces_not_evaluable_with_missing_material():
    result = _result(_expectation([
        {"statement": "近30天按自然日换算", "warrant": ""},
    ]))
    out = apply_interpretation_gate(result)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    assert any(
        INTERPRETATION_UNWARRANTED_TAG in str(item)
        for item in assessment.actual_evidence
    )
    entry = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "interpretation_unwarranted"
    )
    assert entry["cause"] == INTERPRETATION_UNWARRANTED_TAG
    assert entry["missing_material"]
    assert "近30天按自然日换算" in entry["missing_material"][0]


def test_warranted_interpretation_is_consumed_not_vetoed():
    result = _result(_expectation([
        {"statement": "近30天按自然日换算", "warrant": "enhanced_rules:date_window"},
    ]))
    out = apply_interpretation_gate(result)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "fulfilled"
    assert not assessment.evidence_refs


def test_divergent_interpretations_force_not_evaluable_ambiguity():
    # 有担保口径彼此冲突（e 侧显式标 divergent）→ 说不清（口径分歧），不许静默择一。
    result = _result(_expectation([
        {"statement": "按自然日换算", "warrant": "doc:a", "divergent": True},
        {"statement": "按工作日换算", "warrant": "doc:b", "divergent": True},
    ]))
    out = apply_interpretation_gate(result)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    entry = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "interpretation_divergence"
    )
    assert entry["cause"] == INTERPRETATION_DIVERGENCE_TAG
    assert "按自然日换算" in entry["missing_material"][0]
    assert "按工作日换算" in entry["missing_material"][0]


def test_gate_is_idempotent():
    result = _result(_expectation([{"statement": "派生口径", "warrant": ""}]))
    apply_interpretation_gate(result)
    apply_interpretation_gate(result)
    assessment = result.fulfillment_assessments[0]
    kinds = [item.get("kind") for item in assessment.evidence_refs]
    assert kinds.count("interpretation_unwarranted") == 1
    assert len(assessment.actual_evidence) == 1


def test_finalize_runs_gate_before_overall_derivation():
    result = _result(_expectation([{"statement": "派生口径", "warrant": ""}]))
    out = finalize_judge_result(result)
    assert out.fulfillment_assessments[0].status == "not_evaluable"
    assert out.overall_fulfillment["status"] == "not_evaluable"


def test_finalize_keeps_literal_fulfilled():
    result = _result(_expectation())
    out = finalize_judge_result(result)
    assert out.overall_fulfillment["status"] == "fulfilled"


def test_normalize_coerces_bare_string_interpretation_fail_closed():
    expectation = normalize_business_expectation({
        "expectation_id": "核心交付",
        "blocking": True,
        "interpretations": ["裸字符串口径"],
    })
    assert expectation.interpretations == [{"statement": "裸字符串口径"}]
    out = apply_interpretation_gate(_result(expectation))
    assert out.fulfillment_assessments[0].status == "not_evaluable"


def test_authority_gate_accepts_interpretation_cause_tags():
    # 成因枚举对齐：口径无担保/口径分歧是显式成因，不需要 authority 审计，
    # 不得被标 not_evaluable_cause_missing / authority_required_not_consulted。
    assessment = FulfillmentAssessment(
        expectation_id="核心交付",
        status="not_evaluable",
        actual_evidence=[f"{INTERPRETATION_UNWARRANTED_TAG} · 缺料清单：担保材料"],
    )
    result = JudgeResult(
        trace_id="t1",
        project_id="p1",
        business_expectations=[
            BusinessExpectation(expectation_id="核心交付", blocking=True),
        ],
        fulfillment_assessments=[assessment],
    )
    out = apply_authority_gate(result, {})
    kinds = [item.get("kind") for item in out.fulfillment_assessments[0].evidence_refs or []]
    assert "not_evaluable_cause_missing" not in kinds
    assert "authority_required_not_consulted" not in kinds
