from __future__ import annotations

import json
from pathlib import Path

import yaml

from impl.core.judge import build_judge_evidence_view
from impl.core.project_loader import load_project
from impl.core.schema import MockIntentOutput, RunTrace
from impl.projects.policy_search.live_schema import check
from impl.projects.policy_search.rich_mock import build_mock_demands, coverage_summary, normalize_query


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "data" / "policy_search" / "mock_cases.json"
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

    assert len(demands) >= 400
    assert len({normalize_query(item.query) for item in demands}) == len(demands)
    assert summary["covered_field_count"] == summary["enabled_field_count"] == 41
    assert summary["covered_scene_count"] == summary["enabled_scene_count"] == 85
    assert summary["covered_unsupported_scene_count"] == summary["unsupported_scene_count"] == 11


def test_persisted_rich_mock_cases_are_schema_valid_unique_and_golden_independent():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    queries = [str(item["intent"]["query"]) for item in cases]
    normalized = [normalize_query(item) for item in queries]

    assert len(cases) >= 400
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
