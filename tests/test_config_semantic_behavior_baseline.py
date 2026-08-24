from __future__ import annotations

import hashlib
import importlib
import json

from impl.core.check import scan_core_boundary
from impl.core.frontend_view import project_frontend_extensions
from impl.core.interaction_protocol import _project_interactive_scenario
from impl.core.mock_agent import load_live_schema
from impl.core import mock_data_check
from impl.core.project_loader import load_project
from impl.core.schema import RunTrace
from impl.projects.QA.judge import _build_judge_context


PROJECT_IDS = (
    "QA",
    "client_search",
    "deerflow",
    "marketting-planning-intent",
    "marketting-planning",
)

IMPLEMENTATION_CONTRACT_20260721_HASHES = {
    "QA": "6a907cfc91fcce9fc702d557b114eca3ae9503c399a04c0ece0df1d6f670479f",
    "client_search": "bdbaf10213a8b05e3a5072d5abaec29b31aaf2f0cad3a19c710a116ce88edcd5",
    "deerflow": "c757beb8b6cd52c3455ec958fba4e0fe397e6c1c987160ca5278b78a142721bc",
    "marketting-planning": "aa53e67aa16a78508c7b358bd97000c673801ebc7adfb4d996d8716769163918",
    "marketting-planning-intent": "a88f68789a47fe3007627cbc8c91a412c4fe17883ef1fa5a61ece33467b2a8bc",
}


EXPECTED_BEHAVIOR = {
    "QA": {
        "scenarios": ["qa_gold_answer", "qa_context_faithfulness", "qa_weak_quality"],
        "mock_scenarios": ["qa_gold_answer", "qa_context_faithfulness", "qa_weak_quality"],
        "intent_labels": [],
        "ready": ["output", "reference"],
    },
    "client_search": {
        "scenarios": [
            "single_condition",
            "multi_condition_and",
            "product_category_or",
            "product_exclusion",
            "age_boundary",
            "premium_unit_conversion",
            "policy_status_filter",
            "unsupported_family_phrase",
        ],
        "mock_scenarios": [
            "single_condition",
            "multi_condition_and",
            "product_category_or",
            "product_exclusion",
            "age_boundary",
            "premium_unit_conversion",
            "policy_status_filter",
            "unsupported_family_phrase",
        ],
        "intent_labels": [],
        "ready": [],
    },
    "deerflow": {
        "scenarios": [
            "single_turn_planning",
            "multi_turn_dimension_accumulation",
            "clarification",
            "authorization_boundary",
            "non_agent_intent",
            "service_unavailable",
        ],
        "mock_scenarios": [
            "single_turn_planning",
            "multi_turn_dimension_accumulation",
            "clarification",
            "authorization_boundary",
            "service_unavailable",
        ],
        "intent_labels": [],
        "ready": [],
    },
    "marketting-planning-intent": {
        "scenarios": ["intent_recognition", "non_agent_intent", "fallback_unknown"],
        "mock_scenarios": ["intent_recognition", "non_agent_intent", "fallback_unknown"],
        "intent_labels": [
            "other",
            "customer_portrait",
            "nbev_planning",
            "nbev_planning_fallback",
            "achievement_measurement_adjustment",
            "team_portrait",
            "target_value_adjustment",
        ],
        "ready": ["reference"],
    },
    "marketting-planning": {
        "scenarios": [
            "intent_recognition",
            "clarification",
            "multi_turn_field_accumulation",
            "execution_planning",
            "fallback_data_unavailable",
            "non_agent_intent",
            "streaming_protocol",
        ],
        "mock_scenarios": [
            "intent_recognition",
            "clarification",
            "multi_turn_field_accumulation",
            "execution_planning",
            "fallback_data_unavailable",
            "non_agent_intent",
            "streaming_protocol",
        ],
        "intent_labels": [],
        "ready": [],
    },
}


def test_five_project_resolved_behavior_baseline():
    actual = {}
    for project_id in PROJECT_IDS:
        spec = load_project(project_id)
        actual[project_id] = {
            "scenarios": spec.scenarios,
            "mock_scenarios": spec.mock_scenarios,
            "intent_labels": spec.intent_labels,
            "ready": spec.ready,
        }

    assert actual == EXPECTED_BEHAVIOR


def test_typed_implementation_contracts_preserve_20260721_semantics_exactly():
    for project_id, expected_hash in IMPLEMENTATION_CONTRACT_20260721_HASHES.items():
        spec = load_project(project_id)
        contract = {
            "api": dict(spec.application_contract["interface"]),
            "application": {
                key: spec.application_contract[key]
                for key in ("start_run", "boundary")
            },
            **spec.adapter_contract,
            "judge_boundary": spec.judge_boundary_contract,
            "attribution_trace": spec.attribution_trace_contract,
            "frontend_view": spec.frontend_view_contract,
            "batch_persistence": spec.batch_persistence_contract,
            "check_evidence": spec.check_evidence_contract,
        }
        payload = json.dumps(
            contract,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        assert hashlib.sha256(payload).hexdigest() == expected_hash


def test_interactive_scenario_behavior_baseline():
    assert _project_interactive_scenario("deerflow", "multi_turn_dimension_accumulation")
    assert not _project_interactive_scenario("deerflow", "single_turn_planning")
    assert not _project_interactive_scenario("QA", "qa_gold_answer")


def test_qa_judge_context_behavior_baseline():
    spec = load_project("QA")
    context = _build_judge_context(
        spec,
        RunTrace(
            trace_id="baseline-qa",
            project_id="QA",
            reference_contract={"actual_answer": "参考答案"},
        ),
    )

    assert context["score_dimensions"] == [
        "correctness",
        "completeness",
        "key_point_coverage",
        "faithfulness",
        "relevance",
        "usefulness",
        "coherence",
        "risk_control",
        "clarity",
    ]
    assert context["error_taxonomy"] == [
        "answer_incorrect",
        "answer_incomplete",
        "question_misunderstood",
        "irrelevant_answer",
        "unsupported_claim",
        "hallucination",
        "context_not_used",
        "insufficient_context",
        "context_noise",
        "over_refusal",
        "format_error",
        "too_vague",
        "contradiction",
        "needs_human_review",
        "none",
    ]
    assert context["reference_contract"] == {"actual_answer": "参考答案"}


def test_marketing_stream_behavior_baseline():
    spec = load_project("marketting-planning")
    live = importlib.import_module("impl.projects.marketting-planning.live")
    summary = live._event_summary(
        [
            {"event": "reasoning_start"},
            {"event": "card_end"},
            {"event": "heartbeat"},
        ],
        spec,
        business_completed=True,
    )

    assert summary["canonical_names"] == ["intent_detected", "done", "heartbeat"]
    assert summary["protocol_completed"] is True
    assert summary["business_completed"] is True
    assert summary["completed"] is True


def test_check_marker_behavior_baseline(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "example.py").write_text(
        '"""clientAge in a module description is not runtime coupling."""\n'
        '# clientAge in a comment is not runtime coupling.\n'
        'user_intent_summary = "allowed"\n'
        'private_field = "clientAge"\n',
        encoding="utf-8",
    )

    violations = scan_core_boundary(
        tmp_path,
        ["intent_summary", "clientAge"],
    )

    assert not any("intent_summary" in item for item in violations)
    assert any(
        "project-specific marker clientAge" in item
        and "(string)" in item
        for item in violations
    )


def test_check_marker_detects_project_literal_without_prefix_false_positive(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "example.py").write_text(
        'near_match = "prefix-marketting-planning_suffix"\n'
        'registered_project = "marketting-planning"\n',
        encoding="utf-8",
    )

    violations = scan_core_boundary(tmp_path, ["marketting-planning"])

    assert len(violations) == 1
    assert "(string)" in violations[0]


def test_mock_data_check_discovers_projects_from_project_yaml(monkeypatch):
    monkeypatch.setattr(
        mock_data_check,
        "list_projects",
        lambda: ["alpha", "beta"],
    )
    monkeypatch.setattr(
        mock_data_check,
        "check_project",
        lambda project_id: mock_data_check.CheckReport(project_id=project_id),
    )
    monkeypatch.setattr(mock_data_check, "_GLOBAL_CHECK_FUNCTIONS", [])

    reports = mock_data_check.check_all()

    assert list(reports) == ["alpha", "beta", "*global*"]


def test_live_schema_ready_behavior_baseline():
    for project_id in PROJECT_IDS:
        spec = load_project(project_id)
        live_schema = load_live_schema(project_id)

        assert live_schema is not None, project_id
        assert live_schema.check._ready == set(spec.ready), project_id


def test_frontend_projection_behavior_baseline():
    expected_projection_fields = {
        "QA": {"scenarios", "score_dimensions", "error_taxonomy", "core_forbidden_markers"},
        "client_search": {"scenarios", "core_forbidden_markers"},
        "deerflow": {
            "interactive_scenarios",
            "scenarios",
            "stages",
            "dimensions",
            "error_taxonomy",
            "core_forbidden_markers",
            "check_rules",
        },
        "marketting-planning-intent": {
            "scenarios",
            "intent_labels",
            "intent_descriptions",
            "error_taxonomy",
            "core_forbidden_markers",
            "check_rules",
        },
        "marketting-planning": {
            "scenarios",
            "stages",
            "path_types",
            "error_taxonomy",
            "event_aliases",
            "terminal_events",
            "core_forbidden_markers",
            "check_rules",
        },
    }

    for project_id in PROJECT_IDS:
        spec = load_project(project_id)
        extensions = project_frontend_extensions(
            spec,
            RunTrace(trace_id=f"baseline-{project_id}", project_id=project_id),
        )

        assert expected_projection_fields[project_id].issubset(extensions), project_id
        assert extensions["scenarios"] == EXPECTED_BEHAVIOR[project_id]["scenarios"]
