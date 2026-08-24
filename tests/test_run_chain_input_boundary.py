from __future__ import annotations

import pytest

from impl.core import pipeline
from impl.core.interaction_protocol import normalize_case_interaction
from impl.core.schema import RunTrace, SingleTurnCase
from impl.server import service


def _deerflow_request() -> dict:
    return {
        "input": {
            "messages": [
                {"role": "user", "content": "帮我规划某区域的营销活动"},
            ],
        },
        "config": {"configurable": {}},
    }


def _mock_case(*, intent) -> dict:
    return {
        "id": "deerflow-case-1",
        "project_id": "deerflow",
        "scenario": "",
        "intent": intent,
        "live_request": _deerflow_request(),
        "output": None,
        "reference": None,
    }


class _BoundaryReached(RuntimeError):
    pass


def test_pipeline_rejects_ambiguous_dict_boundary():
    with pytest.raises(TypeError, match="runtime SingleTurnCase"):
        pipeline.run_chain("deerflow", _deerflow_request())


@pytest.mark.parametrize("entrypoint", [service.live_run, service.trace_view])
def test_http_live_request_entrypoints_wrap_raw_request(monkeypatch, entrypoint):
    request = _deerflow_request()

    def capture_live_run(project_id, case):
        assert project_id == "deerflow"
        assert isinstance(case, SingleTurnCase)
        assert case.input == request
        return "captured"

    monkeypatch.setattr(service.pipeline, "live_run", capture_live_run)

    assert entrypoint({"project": "deerflow", "input": request}) == "captured"


def test_http_mock_case_entrypoint_preserves_case_semantics(monkeypatch):
    case = _mock_case(intent=None)
    case["output"] = {"answer": "provided"}
    case["reference"] = {"answer": "expected"}

    def capture_live_run(project_id, runtime_case):
        assert project_id == "deerflow"
        assert runtime_case.id == "deerflow-case-1"
        assert runtime_case.input == _deerflow_request()
        assert runtime_case.output == {"answer": "provided"}
        assert runtime_case.reference == {"answer": "expected"}
        assert runtime_case.user_intent == ""
        return "captured"

    monkeypatch.setattr(service.pipeline, "live_run", capture_live_run)

    assert service.live_run({"project": "deerflow", "case": case}) == "captured"


@pytest.mark.parametrize(
    "payload",
    [
        {"project": "deerflow"},
        {"project": "deerflow", "input": {}, "case": _mock_case(intent=None)},
    ],
)
def test_http_boundary_requires_exactly_one_transport_shape(payload):
    with pytest.raises(ValueError, match="exactly one"):
        service.live_run(payload)


def test_run_chain_preserves_typed_case_and_optional_intent(monkeypatch):
    runtime_case = SingleTurnCase(
        id="deerflow-case-1",
        input=_deerflow_request(),
        scenario="single_turn_planning",
        user_intent="",
    )

    def capture_live_run(project_id, case):
        assert project_id == "deerflow"
        assert case is runtime_case
        assert case.user_intent == ""
        raise _BoundaryReached

    monkeypatch.setattr(pipeline, "live_run", capture_live_run)

    with pytest.raises(_BoundaryReached):
        pipeline.run_chain("deerflow", runtime_case)


@pytest.mark.parametrize(
    ("case_intent", "explicit_intent", "expected_intent"),
    [
        ("", None, None),
        ("逐步补齐营销规划维度", None, "逐步补齐营销规划维度"),
        ("原 case 意图", "显式覆盖意图", "显式覆盖意图"),
    ],
)
def test_run_chain_intent_is_optional_and_explicit_override_wins(
    monkeypatch,
    case_intent,
    explicit_intent,
    expected_intent,
):
    runtime_case = SingleTurnCase(
        id="deerflow-case-1",
        input=_deerflow_request(),
        user_intent=case_intent,
    )
    trace = RunTrace(
        trace_id="trace-intent-boundary",
        project_id="deerflow",
        case_id=runtime_case.id,
        input=runtime_case.input,
        normalized_request=runtime_case.input,
    )

    monkeypatch.setattr(pipeline, "live_run", lambda project_id, case: trace)

    def capture_judge(project_id, actual_trace, user_intent=None):
        assert project_id == "deerflow"
        assert actual_trace is trace
        assert user_intent == expected_intent
        raise _BoundaryReached

    monkeypatch.setattr(pipeline, "judge", capture_judge)

    with pytest.raises(_BoundaryReached):
        pipeline.run_chain("deerflow", runtime_case, user_intent=explicit_intent)


@pytest.mark.parametrize(
    ("intent", "expected_user_intent", "has_mock_intent"),
    [
        (None, "", False),
        (
            {
                "user_intent": "逐步补齐营销规划维度",
                "query": "帮我规划某区域的营销活动",
                "user_context": {"role": "营销规划人员"},
                "system_understanding": "系统会逐轮澄清",
                "scenario": "single_turn_planning",
            },
            "逐步补齐营销规划维度",
            True,
        ),
    ],
)
def test_batch_passes_typed_case_without_requiring_intent(
    monkeypatch,
    intent,
    expected_user_intent,
    has_mock_intent,
):
    captured = []

    def capture_run_chain(project_id, case, user_intent=None):
        assert project_id == "deerflow"
        assert isinstance(case, SingleTurnCase)
        captured.append(case)
        return {
            "trace": RunTrace(
                trace_id="trace-1",
                project_id=project_id,
                case_id=case.id,
                input=dict(case.input),
                normalized_request=dict(case.input),
                execution_mode="live",
                output_source="live_service",
            ),
        }

    monkeypatch.setattr(pipeline, "run_chain", capture_run_chain)

    run = pipeline._batch_case(0, _mock_case(intent=intent), "deerflow", None)

    assert run["case_id"] == "deerflow-case-1"
    assert len(captured) == 1
    runtime_case = captured[0]
    assert runtime_case.input == _deerflow_request()
    assert runtime_case.user_intent == expected_user_intent
    assert ("mock_intent" in runtime_case.metadata) is has_mock_intent


def test_optional_intent_does_not_disable_deerflow_multiturn_dispatch():
    runtime_case = SingleTurnCase(
        id="deerflow-multiturn-1",
        input=_deerflow_request(),
        scenario="multi_turn_dimension_accumulation",
        user_intent="",
    )

    normalized = normalize_case_interaction("deerflow", runtime_case)

    assert normalized.mode == "interactive_intent"
    assert normalized.execution_input["input"] == _deerflow_request()
    assert normalized.source_case.get("user_intent", "") == ""
