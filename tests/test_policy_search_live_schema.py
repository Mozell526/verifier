from impl.projects.policy_search.live_schema import check


def _request(args: dict) -> dict:
    return {
        "session_id": "policy-search-schema-test",
        "trace_id": "policy-search-schema-test",
        "extra_input_params": {
            "policySearchParseArgs": {
                "query": "保额不低于50万的保单",
                "currentTime": "2026-08-06 10:30:00",
                "agentCode": "VERIFIER_TEST",
            },
            "args": args,
        },
    }


def test_policy_search_contexts_is_required_by_live_schema():
    assert not check.request(_request({}))
    assert check.request(_request({"contexts": []}))
    assert any("contexts" in error for error in check.request_errors(_request({})))
