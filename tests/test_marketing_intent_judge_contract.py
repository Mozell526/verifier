from __future__ import annotations

import importlib

from impl.core.judge import finalize_judge_result
from impl.core.schema import (
    BusinessExpectation,
    FulfillmentAssessment,
    GapItem,
    JudgeResult,
    RunTrace,
    to_dict,
)


project_judge = importlib.import_module("impl.projects.marketting-planning-intent.judge")


def _trace(
    *,
    intent: str = "nbev_planning",
    confidence: float | None = 0.9,
    required_slots: list[str] | None = None,
    slots: dict | None = None,
    fallback: bool = False,
) -> RunTrace:
    extracted_output = {"intent": intent}
    if confidence is not None:
        extracted_output["confidence"] = confidence
    return RunTrace(
        trace_id="trace-intent",
        project_id="marketting-planning-intent",
        input={"query": "制定年度营销规划"},
        normalized_request={"user_intent": "nbev_planning"},
        extracted_output=extracted_output,
        reference_contract={
            "intent": "nbev_planning",
            "required_slots": list(required_slots or []),
            "min_confidence": 0.8,
            "allow_fallback": False,
        },
        project_fields={
            "intent_evidence": {
                "slots": dict(slots or {}),
                "entities": [],
                "fallback": fallback,
                "ambiguous": False,
            }
        },
    )


def _assessment(result: JudgeResult, expectation_id: str) -> FulfillmentAssessment:
    return next(
        item
        for item in result.fulfillment_assessments
        if item.expectation_id == expectation_id
    )


def test_llm_nonblocking_missing_is_preserved_but_does_not_fail_intent_contract() -> None:
    result = JudgeResult(
        trace_id="trace-intent",
        project_id="marketting-planning-intent",
        business_expectations=[
            BusinessExpectation(
                expectation_id="optional-detail",
                blocking=False,
                expected_outcome="provide an optional explanation",
            )
        ],
        fulfillment_assessments=[
            FulfillmentAssessment(
                expectation_id="optional-detail",
                status="not_fulfilled",
            )
        ],
        missing=[GapItem(kind="missing", expected="optional explanation")],
        reasoning_summary="optional explanation is missing",
    )

    normalized = project_judge.normalize_judge_result(_trace(), result)
    finalized = finalize_judge_result(normalized)

    assert len(finalized.missing) == 1
    assert _assessment(finalized, "intent_contract").status == "fulfilled"
    assert finalized.overall_fulfillment["status"] == "fulfilled"


def test_llm_wrong_gap_is_preserved_but_does_not_drive_project_contract_gate() -> None:
    llm_wrong = GapItem(
        kind="wrong",
        expected="more detailed rationale",
        actual="brief rationale",
        raw={"requirement": "intent"},
    )
    result = JudgeResult(
        trace_id="trace-intent",
        project_id="marketting-planning-intent",
        wrong=[llm_wrong],
    )

    finalized = finalize_judge_result(
        project_judge.normalize_judge_result(_trace(), result)
    )

    assert finalized.wrong[0].raw == {"requirement": "intent"}
    assert _assessment(finalized, "intent_contract").status == "fulfilled"
    assert finalized.overall_fulfillment["status"] == "fulfilled"


def test_deterministic_required_slot_gap_fails_intent_contract() -> None:
    normalized = project_judge.normalize_judge_result(
        _trace(required_slots=["target_value"]),
        JudgeResult(trace_id="trace-intent", project_id="marketting-planning-intent"),
    )
    finalized = finalize_judge_result(normalized)

    assessment = _assessment(finalized, "intent_contract")
    assert assessment.status == "not_fulfilled"
    assert assessment.expected_evidence
    assert assessment.actual_evidence[0]["contract_missing"] == ["required_slots"]
    assert assessment.downstream_impact
    assert finalized.overall_fulfillment["status"] == "not_fulfilled"


def test_deterministic_intent_mismatch_fails_intent_contract() -> None:
    finalized = finalize_judge_result(project_judge.normalize_judge_result(
        _trace(intent="fallback"),
        JudgeResult(trace_id="trace-intent", project_id="marketting-planning-intent"),
    ))

    assessment = _assessment(finalized, "intent_contract")
    assert assessment.status == "not_fulfilled"
    assert "intent" in assessment.actual_evidence[0]["contract_wrong"]
    assert finalized.overall_fulfillment["status"] == "not_fulfilled"


def test_disallowed_fallback_fails_intent_contract() -> None:
    finalized = finalize_judge_result(project_judge.normalize_judge_result(
        _trace(fallback=True),
        JudgeResult(trace_id="trace-intent", project_id="marketting-planning-intent"),
    ))

    assessment = _assessment(finalized, "intent_contract")
    assert "allow_fallback" in assessment.actual_evidence[0]["contract_wrong"]
    assert finalized.overall_fulfillment["status"] == "not_fulfilled"


def test_low_or_missing_confidence_fails_intent_contract() -> None:
    low = finalize_judge_result(project_judge.normalize_judge_result(
        _trace(confidence=0.4),
        JudgeResult(trace_id="trace-intent", project_id="marketting-planning-intent"),
    ))
    missing = finalize_judge_result(project_judge.normalize_judge_result(
        _trace(confidence=None),
        JudgeResult(trace_id="trace-intent", project_id="marketting-planning-intent"),
    ))

    assert "min_confidence" in _assessment(low, "intent_contract").actual_evidence[0]["contract_wrong"]
    assert "confidence" in _assessment(missing, "intent_contract").actual_evidence[0]["contract_missing"]
    assert low.overall_fulfillment["status"] == "not_fulfilled"
    assert missing.overall_fulfillment["status"] == "not_fulfilled"


def test_existing_blocking_failure_remains_blocking_when_intent_contract_passes() -> None:
    result = JudgeResult(
        trace_id="trace-intent",
        project_id="marketting-planning-intent",
        business_expectations=[
            BusinessExpectation(
                expectation_id="dispatch-boundary",
                blocking=True,
                expected_outcome="route only to an allowed downstream",
            )
        ],
        fulfillment_assessments=[
            FulfillmentAssessment(
                expectation_id="dispatch-boundary",
                status="not_fulfilled",
            )
        ],
    )

    finalized = finalize_judge_result(
        project_judge.normalize_judge_result(_trace(), result)
    )

    assert _assessment(finalized, "intent_contract").status == "fulfilled"
    assert _assessment(finalized, "dispatch-boundary").status == "not_fulfilled"
    assert finalized.overall_fulfillment["status"] == "not_fulfilled"


def test_existing_intent_contract_expectation_metadata_is_preserved() -> None:
    existing = BusinessExpectation(
        expectation_id="intent_contract",
        blocking=False,
        user_intent="preserve-me",
        required_capabilities=["project-specific-capability"],
        boundary={"tenant": "existing"},
        evidence_refs=["existing-ref"],
    )
    normalized = project_judge.normalize_judge_result(
        _trace(),
        JudgeResult(
            trace_id="trace-intent",
            project_id="marketting-planning-intent",
            business_expectations=[existing],
        ),
    )
    preserved = next(
        item
        for item in normalized.business_expectations
        if item.expectation_id == "intent_contract"
    )

    assert preserved.blocking is True
    assert preserved.user_intent == "preserve-me"
    assert preserved.required_capabilities == ["project-specific-capability"]
    assert preserved.boundary == {"tenant": "existing"}
    assert preserved.evidence_refs == ["existing-ref"]


def test_intent_contract_normalize_is_idempotent() -> None:
    trace = _trace(required_slots=["target_value"])
    once = project_judge.normalize_judge_result(
        trace,
        JudgeResult(trace_id="trace-intent", project_id="marketting-planning-intent"),
    )
    once_snapshot = to_dict(once)
    twice = project_judge.normalize_judge_result(trace, once)

    assert to_dict(twice) == once_snapshot
    assert sum(
        item.expectation_id == "intent_contract"
        for item in twice.business_expectations
    ) == 1
    assert sum(
        item.expectation_id == "intent_contract"
        for item in twice.fulfillment_assessments
    ) == 1
