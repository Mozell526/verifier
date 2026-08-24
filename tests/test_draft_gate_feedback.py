import json
from pathlib import Path

from impl.core.draft_gate_feedback import (
    build_authority_gate_feedback,
    render_gate_feedback,
    write_gate_feedback,
)


def test_runtime_replay_failure_is_explicit_authority_solidify_feedback(tmp_path: Path):
    feedback = build_authority_gate_feedback(
        project_id="demo",
        role="judge",
        owner_stage="solidify",
        error=(
            "Authority Runtime Replay missing: Solidify smoke must prove real "
            "authority.resolve calls for frozen Investigation probes"
        ),
        affected_subjects=("subject:operator", "subject:mapping"),
    )

    assert feedback["authority_problem"] is True
    assert feedback["owner_stage"] == "solidify"
    assert feedback["gate"] == "AUTHORITY_RUNTIME_REPLAY"
    assert "authority.resolve" in feedback["diagnosis"]
    assert any("tool_call_id" in item for item in feedback["improvement_options"])
    assert any("expected_status" in item for item in feedback["prohibited_shortcuts"])

    prompt = render_gate_feedback(feedback)
    assert "Draft Authority Gate Feedback" in prompt
    assert "Authority Runtime" in prompt
    assert "subject:operator" in prompt

    path = write_gate_feedback(tmp_path / "feedback.json", feedback)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["harness_prompt"] == prompt


def test_claim_failure_routes_harness_back_to_investigate():
    feedback = build_authority_gate_feedback(
        project_id="demo",
        role="judge",
        owner_stage="investigate",
        error="Authority claim conflict has neither resolution nor coverage gap: subject:one",
    )

    assert feedback["gate"] == "AUTHORITY_INVESTIGATION_CLAIMS"
    assert feedback["owner_stage"] == "investigate"
    assert "Claim" in feedback["diagnosis"]
    assert "Resolution" in feedback["pass_condition"]


def test_material_drift_is_explained_as_authority_investigation_staleness():
    feedback = build_authority_gate_feedback(
        project_id="demo",
        role="judge",
        owner_stage="investigate",
        error="EvidenceRef content hash changed: policy-source",
    )

    assert feedback["gate"] == "AUTHORITY_MATERIAL_FRESHNESS"
    assert "revision/hash" in feedback["diagnosis"]
    assert any("重新 Load" in item for item in feedback["improvement_options"])


def test_unknown_authority_contract_source_routes_to_solidify_mapping():
    feedback = build_authority_gate_feedback(
        project_id="demo",
        role="judge",
        owner_stage="solidify",
        error=(
            "Solidify mapping references unknown contract source ID: "
            "authority-claim-index"
        ),
    )

    assert feedback["gate"] == "AUTHORITY_SOLIDIFY_MAPPING"
    assert feedback["owner_stage"] == "solidify"
    assert feedback["diagnosis_code"] == "authority_assets_not_solidified"


def test_judge_obligation_gate_reports_actionable_final_model_failures():
    from impl.core.draft_gate_feedback import analyze_judge_gate_obligations

    result = {
        "business_expectations": [
            {"expectation_id": "core-search", "blocking": True},
            {"expectation_id": "safe-refusal", "blocking": True},
        ],
        "fulfillment_assessments": [
            {"expectation_id": "core-search", "status": "fulfilled", "authority_tool_call_ids": []},
            {"expectation_id": "safe-refusal", "status": "fulfilled", "authority_tool_call_ids": []},
        ],
        "overall_fulfillment": {"status": "fulfilled"},
    }
    gate = analyze_judge_gate_obligations(
        result=result,
        runtime={"authority_audit": {}, "authority_tool_call_ids": []},
        obligations=[{
            "subject": "semantic-carrier:organization-name",
            "trigger": "missing_semantic_carrier",
            "authority_required": True,
            "blocking_expectation_ids": ["core-search"],
            "expected_non_blocking_expectation_ids": ["safe-refusal"],
        }],
    )

    assert gate["status"] == "failed"
    assert gate["finding_counts"] == {
        "not_called": 1,
        "safety_expectation_marked_blocking": 1,
    }
    assert {item["owner"] for item in gate["findings"]} == {
        "candidate_judge_trigger_logic",
        "candidate_judge_expectation_construction",
    }


def test_judge_obligation_gate_accepts_unresolved_consumed_by_dependent_item_only():
    from impl.core.draft_gate_feedback import analyze_judge_gate_obligations

    call_id = "authority.demo.abc123"
    result = {
        "business_expectations": [
            {"expectation_id": "core", "blocking": True},
            {"expectation_id": "safe", "blocking": False},
        ],
        "fulfillment_assessments": [
            {"expectation_id": "core", "status": "not_evaluable", "authority_tool_call_ids": [call_id]},
            {"expectation_id": "safe", "status": "fulfilled", "authority_tool_call_ids": []},
        ],
        "overall_fulfillment": {"status": "not_evaluable"},
    }
    gate = analyze_judge_gate_obligations(
        result=result,
        runtime={
            "authority_tool_call_ids": [call_id],
            "authority_audit": {call_id: {"resolution": {"status": "unresolved"}}},
        },
        obligations=[{
            "subject": "operator:range",
            "trigger": "operator_contract_conflict",
            "authority_required": True,
            "blocking_expectation_ids": ["core"],
            "expected_non_blocking_expectation_ids": ["safe"],
        }],
    )

    assert gate["status"] == "passed"
    assert gate["findings"] == []


def test_judge_obligation_gate_accepts_contradicted_when_judge_already_rejected_claim():
    from impl.core.draft_gate_feedback import analyze_judge_gate_obligations

    call_id = "authority.demo.contradicted"
    result = {
        "business_expectations": [
            {"expectation_id": "core", "blocking": True},
        ],
        "fulfillment_assessments": [
            {
                "expectation_id": "core",
                "status": "not_fulfilled",
                "authority_tool_call_ids": [call_id],
            },
        ],
        "overall_fulfillment": {"status": "not_fulfilled"},
    }
    gate = analyze_judge_gate_obligations(
        result=result,
        runtime={
            "authority_tool_call_ids": [call_id],
            "authority_audit": {
                call_id: {"resolution": {"status": "contradicted"}},
            },
        },
        obligations=[{
            "subject": "mapping:orphanType",
            "trigger": "normative_rule",
            "authority_required": True,
            "blocking_expectation_ids": ["core"],
        }],
    )

    assert gate["status"] == "passed"
    assert gate["findings"] == []


def test_judge_obligation_gate_distinguishes_three_finding_types():
    from impl.core.draft_gate_feedback import analyze_judge_gate_obligations

    base = {
        "business_expectations": [{"expectation_id": "core", "blocking": True}],
        "fulfillment_assessments": [{"expectation_id": "core", "status": "fulfilled", "authority_tool_call_ids": []}],
        "overall_fulfillment": {"status": "fulfilled"},
    }
    def run(obligation):
        return analyze_judge_gate_obligations(result=base, runtime={}, obligations=[obligation])

    judge_failed = run({
        "subject": "rule:a", "trigger": "normative_rule", "authority_required": True,
        "authority_availability": "available", "blocking_expectation_ids": ["core"],
    })
    assert judge_failed["finding_counts"]["not_called"] == 1
    assert judge_failed["findings"][0]["finding_type"] == "judge_failed_to_call"
    assert judge_failed["findings"][0]["remediation_target"]

    availability = run({
        "subject": "rule:b", "trigger": "normative_rule", "authority_required": True,
        "authority_availability": "unavailable", "blocking_expectation_ids": ["core"],
    })
    assert availability["finding_counts"]["availability_miss"] == 1
    assert availability["findings"][0]["finding_type"] == "availability_miss"

    compaction = run({
        "subject": "rule:c", "trigger": "normative_rule", "authority_required": True,
        "authority_availability": "available", "full_material_governs": True,
        "compact_projection_visible": False, "blocking_expectation_ids": ["core"],
    })
    assert compaction["finding_counts"]["compaction_miss"] == 1
    assert compaction["findings"][0]["finding_type"] == "compaction_miss"


def test_gate_replay_scores_only_closed_loop_labels_and_requires_actionable_findings():
    from impl.core.draft_gate_feedback import score_judge_gate_replay

    finding = {"finding_type": "judge_failed_to_call", "remediation_target": "candidate judge prompt"}
    report = score_judge_gate_replay([
        {"case_id": "dirty-1", "label_quality": "closed_loop", "expected_gate": "dirty", "gate": {"findings": [finding]}},
        {"case_id": "dirty-2", "label_quality": "closed_loop", "expected_gate": "dirty", "gate": {"findings": [finding]}},
        {"case_id": "clean-1", "label_quality": "closed_loop", "expected_gate": "clean", "gate": {"findings": []}},
        {"case_id": "reference-boundary", "label_quality": "boundary", "expected_gate": "dirty", "gate": {"findings": []}},
    ])
    assert report["status"] == "passed"
    assert report["dirty_recall"] == 1.0
    assert report["boundary_observation_count"] == 1
    assert report["boundary_case_ids"] == ["reference-boundary"]


def test_gate_replay_fails_when_findings_are_not_actionable():
    from impl.core.draft_gate_feedback import score_judge_gate_replay

    report = score_judge_gate_replay([
        {"case_id": "dirty", "label_quality": "closed_loop", "expected_gate": "dirty", "gate": {"findings": [{"finding_type": "availability_miss"}]}},
        {"case_id": "clean", "label_quality": "closed_loop", "expected_gate": "clean", "gate": {"findings": []}},
    ])
    assert report["status"] == "failed"
    assert report["actionable_finding_rate"] == 0.0
