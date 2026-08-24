from __future__ import annotations

from copy import deepcopy

from impl.core.schema import LiveExchange, RunTrace, to_public_dict
from impl.projects.policy_search.live_schema import check
from impl.server.service import compact_run


def _policy_search_request(*, contexts: list[dict] | None = None) -> dict:
    return {
        "session_id": "schema-preserving-request",
        "trace_id": "schema-preserving-request",
        "extra_input_params": {
            "policySearchParseArgs": {
                "query": "张三或李四作为投保人，今年生效且保额不低于50万的保单",
                "currentTime": "2026-08-06 10:30:00",
                "agentCode": "A12345678",
            },
            "args": {"contexts": list(contexts or [])},
        },
        "history": [],
        "application_setting": None,
        "scenario": None,
    }


def test_run_trace_preserves_live_request_facts_exactly() -> None:
    request = _policy_search_request()
    assert check.request(request)
    exchange = LiveExchange(
        exchange_id="exchange-1",
        sequence=0,
        transport="http",
        method="POST",
        url="http://127.0.0.1:8050/api/v1/policy-search/parse",
        carries_live_request=True,
        contributes_raw_response=True,
        request=deepcopy(request),
    )
    trace = RunTrace(
        trace_id="policy_search:schema-preserving-request",
        project_id="policy_search",
        input=deepcopy(request),
        normalized_request=deepcopy(request),
        turn_records=[{
            "turn_index": 1,
            "request": deepcopy(request),
            "live_exchanges": [exchange],
            "call_status": "succeeded",
        }],
        status="ok",
    )

    public = to_public_dict(trace)
    serialized_requests = (
        public["input"],
        public["normalized_request"],
        public["turn_records"][0]["request"],
        public["turn_records"][0]["live_exchanges"][0]["request"],
    )

    assert all(item == request for item in serialized_requests)
    assert all(check.request(item) for item in serialized_requests)
    assert all(item["extra_input_params"]["args"]["contexts"] == [] for item in serialized_requests)
    assert all(item["history"] == [] for item in serialized_requests)
    assert all(item["application_setting"] is None for item in serialized_requests)


def test_request_fact_serialization_does_not_sanitize_invalid_request() -> None:
    request = _policy_search_request(contexts=[{
        "role": "user",
        "content": "查张三作为投保人的保单",
        "sub_agent": "",
    }])
    request["extra_input_params"]["args"]["unexpected_empty"] = []
    assert not check.request(request)

    public = to_public_dict(RunTrace(
        trace_id="policy_search:invalid-request",
        project_id="policy_search",
        input=deepcopy(request),
        status="failed",
    ))

    assert public["input"] == request
    assert "unexpected_empty" in public["input"]["extra_input_params"]["args"]
    assert not check.request(public["input"])


def test_request_preservation_does_not_disable_public_trace_compaction() -> None:
    request = _policy_search_request()
    public = to_public_dict(RunTrace(
        trace_id="policy_search:public-compaction",
        project_id="policy_search",
        input=request,
        reference_contract={},
        runtime_logs=["private runtime log"],
        status="ok",
    ))

    assert public["input"] == request
    assert "reference_contract" not in public
    assert "runtime_logs" not in public
    assert "error" not in public


def test_public_trace_serialization_is_idempotent() -> None:
    request = _policy_search_request()
    trace = _trace_with_all_request_facts(request)

    once = to_public_dict(trace)
    twice = to_public_dict(once)

    assert twice == once
    _assert_all_requests_preserved(twice, request)


def test_batch_status_serialization_preserves_all_request_facts() -> None:
    request = _policy_search_request()
    compact = compact_run({"trace": _trace_with_all_request_facts(request)})

    public = to_public_dict({
        "events": [{"run": compact}],
        "result": {"runs": [compact]},
    })

    _assert_all_requests_preserved(public["events"][0]["run"]["trace"], request)
    _assert_all_requests_preserved(public["result"]["runs"][0]["trace"], request)
    assert "runtime_logs" not in public["events"][0]["run"]["trace"]
    assert "runtime_logs" not in public["result"]["runs"][0]["trace"]


def _trace_with_all_request_facts(request: dict) -> RunTrace:
    exchange = LiveExchange(
        exchange_id="exchange-batch",
        sequence=0,
        transport="http",
        method="POST",
        url="http://127.0.0.1:8050/api/v1/policy-search/parse",
        carries_live_request=True,
        contributes_raw_response=True,
        request=deepcopy(request),
    )
    return RunTrace(
        trace_id="policy_search:batch-schema-preserving-request",
        project_id="policy_search",
        input=deepcopy(request),
        normalized_request=deepcopy(request),
        turn_records=[{
            "turn_index": 1,
            "request": deepcopy(request),
            "live_exchanges": [exchange],
        }],
        runtime_logs=["private runtime log"],
        status="ok",
    )


def _assert_all_requests_preserved(trace: dict, request: dict) -> None:
    serialized_requests = (
        trace["input"],
        trace["normalized_request"],
        trace["turn_records"][0]["request"],
        trace["turn_records"][0]["live_exchanges"][0]["request"],
    )
    assert all(item == request for item in serialized_requests)
    assert all(check.request(item) for item in serialized_requests)
