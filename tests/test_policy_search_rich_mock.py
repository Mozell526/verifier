from __future__ import annotations

import json
from pathlib import Path

import yaml

from impl.core.judge import build_judge_evidence_view
from impl.core.project_loader import load_project
from impl.core.schema import MockIntentOutput, RunTrace
from impl.projects.policy_search.live_schema import check
from impl.projects.policy_search.rich_mock import MockDemand, build_mock_demands, build_multiturn_demands, coverage_summary, normalize_query


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "data" / "policy_search" / "mock_cases.json"
MULTITURN_CASES_PATH = ROOT / "data" / "policy_search" / "mock_cases-multiturn.json"
COVERAGE_PATH = ROOT / "impl" / "data" / "policy_search" / "mock_coverage.json"


def _business_config() -> dict:
    spec = load_project("policy_search")
    return json.loads(Path(spec.source_path("business_config")).read_text(encoding="utf-8"))


def _golden_queries() -> set[str]:
    spec = load_project("policy_search")
    manifest_path = Path(spec.source_path("golden_manifest"))
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    queries: set[str] = set()
    for relative in manifest.get("case_files") or []:
        for line in (manifest_path.parent / str(relative)).read_text(encoding="utf-8").splitlines():
            if line.strip():
                query = str(json.loads(line).get("query") or "")
                if query:
                    queries.add(normalize_query(query))
    return queries


def test_rich_mock_planner_covers_business_capabilities_without_duplicates():
    config = _business_config()
    demands = build_mock_demands(config)
    summary = coverage_summary(demands, config)

    assert len(demands) >= 350
    assert len({normalize_query(item.query) for item in demands}) == len(demands)
    assert summary["covered_field_count"] == summary["enabled_field_count"] == 41
    assert summary["covered_scene_count"] == summary["enabled_scene_count"] == 85
    assert summary["covered_unsupported_scene_count"] == summary["unsupported_scene_count"] == 11


def test_persisted_rich_mock_cases_are_schema_valid_unique_and_golden_independent():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    queries = [str(item["intent"]["query"]) for item in cases]
    normalized = [normalize_query(item) for item in queries]

    assert len(cases) >= 350
    assert len({item["id"] for item in cases}) == len(cases)
    assert len(set(normalized)) == len(normalized)
    assert not set(normalized).intersection(_golden_queries())
    assert all(check.request(item["live_request"]) for item in cases)
    assert all(item["output"] is None and item["reference"] is None for item in cases)
    assert coverage["case_count"] == len(cases)
    assert coverage["covered_field_count"] == coverage["enabled_field_count"]
    assert coverage["covered_scene_count"] == coverage["enabled_scene_count"]
    assert coverage["covered_unsupported_scene_count"] == coverage["unsupported_scene_count"]


def test_coverage_metadata_and_expected_answers_do_not_enter_mock_cases():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    forbidden_keys = {"coverage", "field_ids", "scene_ids", "operator_family", "expected_status", "expected_filter"}

    def keys(value):
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value)) if value else set()
        return set()

    assert all(not forbidden_keys.intersection(keys(case)) for case in cases)


def test_judge_evidence_excludes_mock_user_context():
    sentinel = "COVERAGE_ONLY_DO_NOT_SEND_TO_JUDGE"
    request = {
        "session_id": "judge-isolation",
        "trace_id": "judge-isolation",
        "extra_input_params": {
            "policySearchParseArgs": {
                "query": "保额至少30万的保单",
                "currentTime": "2026-08-06 10:30:00",
                "agentCode": "VERIFIER_TEST",
            },
            "args": {"contexts": []},
        },
    }
    trace = RunTrace(
        trace_id="policy_search:judge-isolation",
        project_id="policy_search",
        input=request,
        normalized_request=request,
        extracted_output={"status": "SUCCESS", "filter": {"type": "PREDICATE"}},
        mock_intent=MockIntentOutput(
            user_intent="筛选保额至少30万元的保单",
            query="保额至少30万的保单",
            user_context={"coverage_tag": sentinel},
            scenario="atomic_condition",
        ),
        status="ok",
    )

    evidence = build_judge_evidence_view(trace)

    assert sentinel not in json.dumps(evidence, ensure_ascii=False)
    assert "coverage_tag" not in json.dumps(evidence, ensure_ascii=False)


_SCHEMA_LABEL_STUFFING = (
    "投资属性",
    "保障属性",
    "是否在犹豫期",
    "投被保人关系",
    "犹豫期剩余天数",
    "保单周年日的保单",
    "是否自保件",
    "是否有效的保单",
)


_FACT_CONTRACT_MARKERS = ("还没想好", "还没定", "还没说", "一时想不起来", "具体多少")


def test_multiturn_demands_are_handwritten_pairs_not_field_coverage():
    config = _business_config()
    demands = build_multiturn_demands(config)
    reply = [item for item in demands if item.scenario == "clarification_reply"]
    switched = [item for item in demands if item.scenario == "clarification_then_new_query"]
    queries = [item.query for item in demands]
    next_queries = [item.next_query for item in demands]

    assert reply
    assert switched
    assert len(reply) > len(switched)
    assert all(item.query and item.next_query and item.user_intent for item in demands)
    assert len({item.demand_id for item in demands}) == len(demands)
    assert {item.scenario for item in demands} == {"clarification_reply", "clarification_then_new_query"}
    assert not any(query.startswith("我想") for query in queries)
    assert not any(query.startswith("先问") for query in queries)
    assert all("保单" in item.query or "单" in item.query for item in demands)
    assert not any(item.query in {"尾号", "状态呢", "三万到", "犹豫期呢", "怎么交费"} for item in demands)
    assert all("保单" in item.next_query or "单" in item.next_query for item in switched)
    assert not any(any(marker in query for marker in _FACT_CONTRACT_MARKERS) for query in queries + next_queries)
    assert not any(any(marker in query for marker in _SCHEMA_LABEL_STUFFING) for query in queries)
    unique_t1 = {normalize_query(item.query) for item in demands}
    assert len(unique_t1) >= 20
    short_replies = [item for item in reply if len(item.next_query) <= 8]
    assert short_replies
    assert all(item.query != item.next_query for item in demands)


def test_multiturn_demand_template_uses_handwritten_speech():
    from impl.projects.policy_search.mock import demand_template

    empty = MockDemand(
        demand_id="mt-empty",
        scenario="clarification_reply",
        user_intent="残缺保额筛选",
        query="",
        coverage={"kind": "clarification_reply"},
    )
    handwritten = MockDemand(
        demand_id="mt-handwritten",
        scenario="clarification_reply",
        user_intent="用尾号补保单号",
        query="查一下尾号",
        next_query="4826",
    )

    assert "mock_query" not in demand_template(empty)
    template = demand_template(handwritten)
    assert template["mock_query"] == "查一下尾号"
    assert template["next_query"] == "4826"


def test_persisted_multiturn_mock_cases_are_interactive_and_schema_valid():
    cases = json.loads(MULTITURN_CASES_PATH.read_text(encoding="utf-8"))
    scenarios = {item["scenario"] for item in cases}
    queries = [str(item["intent"]["query"]) for item in cases]
    next_queries = [str(((item.get("intent") or {}).get("user_context") or {}).get("next_query") or "") for item in cases]
    keys = [
        (
            item["scenario"],
            normalize_query(item["intent"]["query"]),
            normalize_query(((item.get("intent") or {}).get("user_context") or {}).get("next_query") or ""),
        )
        for item in cases
    ]

    assert 20 <= len(cases) <= 80
    assert scenarios == {"clarification_reply", "clarification_then_new_query"}
    assert all(next_queries)
    assert len({item["id"] for item in cases}) == len(cases)
    assert len(set(keys)) == len(keys)
    assert all(str(item["id"]).startswith("policy-search-mt-") for item in cases)
    assert all(check.request(item["live_request"]) for item in cases)
    assert all(item["output"] is None and item["reference"] is None for item in cases)
    assert all(((item["live_request"]["extra_input_params"].get("args") or {}).get("contexts") or []) == [] for item in cases)
    assert all(item["live_request"]["extra_input_params"]["policySearchParseArgs"]["query"] == item["intent"]["query"] for item in cases)
    assert not {normalize_query(query) for query in queries + next_queries}.intersection(_golden_queries())
    assert not any(query.startswith("我想") for query in queries)
    assert not any(query.startswith("先问") for query in queries)
    assert all("保单" in query or "单" in query for query in queries)
    assert not any(query in {"尾号", "状态呢", "三万到", "犹豫期呢", "怎么交费"} for query in queries)
    assert not any(any(marker in text for marker in _FACT_CONTRACT_MARKERS) for text in queries + next_queries)
    assert not any(any(marker in query for marker in _SCHEMA_LABEL_STUFFING) for query in queries)
    assert sum(1 for query in queries if query.startswith("我想")) / len(queries) < 0.1
    switched_next = [str(((item.get("intent") or {}).get("user_context") or {}).get("next_query") or "") for item in cases if item["scenario"] == "clarification_then_new_query"]
    assert all("保单" in text or "单" in text for text in switched_next)


def test_last_turn_context_cases_wear_live_clarification():
    config = _business_config()
    demands = [item for item in build_mock_demands(config) if item.scenario == "context_disambiguation"]
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    ctx_cases = [item for item in cases if item["scenario"] == "context_disambiguation"]
    from impl.projects.policy_search.rich_mock import _prior_assistant_content, _prior_live_cache

    assert len(demands) >= 20
    assert len(ctx_cases) == len(demands)
    for item in ctx_cases:
        contexts = ((item.get("live_request") or {}).get("extra_input_params") or {}).get("args", {}).get("contexts") or []
        intent_contexts = ((item.get("intent") or {}).get("user_context") or {}).get("contexts") or []
        assert len(contexts) == 2
        assert contexts == intent_contexts
        prev = next(row["content"] for row in contexts if row.get("role") == "user")
        assistant = next(row["content"] for row in contexts if row.get("role") == "assistant")
        query = str(item["intent"]["query"])
        assert "保单" in prev or "单" in prev
        assert assistant
        assert assistant != "解析成功"
        assert _prior_live_cache()[prev]["status"] == "UNSUPPORTED"
        assert assistant == _prior_assistant_content(prev)
        assert query != prev
        assert item["live_request"]["extra_input_params"]["policySearchParseArgs"]["query"] == query


