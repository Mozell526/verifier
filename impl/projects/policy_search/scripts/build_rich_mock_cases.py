"""生成并校验 Policy Search 高丰富度 MockCase。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml

from impl.core.project_loader import load_project
from impl.core.schema import MockCase, MockIntentOutput, to_dict
from impl.projects.policy_search.live_schema import check
from impl.projects.policy_search.mock import PolicySearchMock
from impl.projects.policy_search.rich_mock import (
    MockDemand,
    build_mock_demands,
    coverage_summary,
    normalize_query,
)


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CASES_PATH = ROOT / "impl" / "data" / "policy_search" / "mock_cases.json"
DEFAULT_COVERAGE_PATH = ROOT / "impl" / "data" / "policy_search" / "mock_coverage.json"


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"expected JSON object: {path}")
    return document


def _golden_queries(manifest_path: Path) -> list[str]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    queries: list[str] = []
    for relative in manifest.get("case_files") or []:
        path = manifest_path.parent / str(relative)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            query = str(payload.get("query") or "").strip()
            if query:
                queries.append(query)
    return queries


def _stable_request(case: Any, index: int) -> None:
    case_id = f"policy-search-rich-{index:04d}"
    case.id = case_id
    request = dict(case.input or {})
    request["session_id"] = case_id
    request["trace_id"] = case_id
    case.input = request


def _case_payload(mock: PolicySearchMock, demand: MockDemand, index: int) -> dict[str, Any]:
    runtime_case = mock.generate_demand_case(demand)
    _stable_request(runtime_case, index)
    stored = MockCase(
        id=runtime_case.id,
        project_id="policy_search",
        scenario=demand.scenario,
        intent=MockIntentOutput(
            user_intent=demand.user_intent,
            query=demand.query,
            user_context={"contexts": list(demand.contexts)} if demand.contexts else {},
            system_understanding="用户通过自然语言筛选保单，系统返回查询语法树而非保单列表。",
            scenario=demand.scenario,
        ),
        live_request=dict(runtime_case.input or {}),
        output=None,
        reference=None,
    )
    payload = to_dict(stored)
    if not check.request(payload["live_request"]):
        raise ValueError(f"request schema failed: {demand.demand_id}: {check.request_errors(payload['live_request'])}")
    return payload


def build_dataset() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = load_project("policy_search")
    business_config_path = Path(spec.source_path("business_config"))
    golden_manifest_path = Path(spec.source_path("golden_manifest"))
    config = _load_json(business_config_path)

    # 生成阶段只接收业务能力配置；golden 文本在全部候选生成完成后才加载。
    planned = build_mock_demands(config)
    mock = PolicySearchMock(spec)
    generated = [(demand, _case_payload(mock, demand, index)) for index, demand in enumerate(planned, start=1)]

    golden_queries = _golden_queries(golden_manifest_path)
    normalized_golden = {normalize_query(item) for item in golden_queries}
    accepted: list[tuple[MockDemand, dict[str, Any]]] = []
    rejected_exact: list[dict[str, str]] = []
    for demand, case in generated:
        if normalize_query(demand.query) in normalized_golden:
            rejected_exact.append({"demand_id": demand.demand_id, "query": demand.query})
            continue
        accepted.append((demand, case))

    # 剔除 golden 重复后重新编号，保持 case ID 连续稳定。
    cases: list[dict[str, Any]] = []
    coverage_items: list[dict[str, Any]] = []
    for index, (demand, case) in enumerate(accepted, start=1):
        case_id = f"policy-search-rich-{index:04d}"
        case["id"] = case_id
        case["live_request"]["session_id"] = case_id
        case["live_request"]["trace_id"] = case_id
        cases.append(case)
        coverage_items.append({
            "case_id": case_id,
            "demand_id": demand.demand_id,
            "scenario": demand.scenario,
            **dict(demand.coverage),
        })

    normalized = [normalize_query(item["intent"]["query"]) for item in cases]
    duplicates = sorted(value for value, count in Counter(normalized).items() if count > 1)
    if duplicates:
        raise ValueError(f"normalized duplicate queries: {duplicates[:10]}")

    golden_sample = list(dict.fromkeys(golden_queries))
    high_similarity: list[dict[str, Any]] = []
    for demand, _case in accepted:
        best_query = ""
        best_ratio = 0.0
        for golden in golden_sample:
            ratio = SequenceMatcher(None, normalize_query(demand.query), normalize_query(golden)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_query = golden
        if best_ratio >= 0.90:
            high_similarity.append({
                "demand_id": demand.demand_id,
                "query": demand.query,
                "golden_query": best_query,
                "similarity": round(best_ratio, 4),
            })

    summary = coverage_summary((item for item, _case in accepted), config)
    expected_fields = summary["enabled_field_count"]
    expected_scenes = summary["enabled_scene_count"]
    expected_unsupported = summary["unsupported_scene_count"]
    if summary["case_count"] < 400:
        raise ValueError(f"case_count below target: {summary['case_count']} < 400")
    if summary["covered_field_count"] != expected_fields:
        raise ValueError(f"field coverage incomplete: {summary['covered_field_count']} / {expected_fields}")
    if summary["covered_scene_count"] != expected_scenes:
        raise ValueError(f"scene coverage incomplete: {summary['covered_scene_count']} / {expected_scenes}")
    if summary["covered_unsupported_scene_count"] != expected_unsupported:
        raise ValueError(
            "unsupported coverage incomplete: "
            f"{summary['covered_unsupported_scene_count']} / {expected_unsupported}"
        )

    report = {
        "schema_version": 1,
        "generator": "policy_search.rich_mock",
        "generation_source": "business capability config only; golden queries excluded from generation",
        "judge_isolation": {
            "coverage_metadata_in_mock_case": False,
            "coverage_metadata_in_judge_evidence": False,
            "user_context_contains_expected_answer": False,
        },
        **summary,
        "exact_golden_rejections": rejected_exact,
        "high_similarity_review": high_similarity,
        "cases": coverage_items,
    }
    return cases, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-output", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--coverage-output", type=Path, default=DEFAULT_COVERAGE_PATH)
    args = parser.parse_args()
    cases, coverage = build_dataset()
    args.cases_output.parent.mkdir(parents=True, exist_ok=True)
    args.coverage_output.parent.mkdir(parents=True, exist_ok=True)
    args.cases_output.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.coverage_output.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases_output": str(args.cases_output),
        "coverage_output": str(args.coverage_output),
        "case_count": len(cases),
        "scenario_counts": coverage["scenario_counts"],
        "exact_golden_rejections": len(coverage["exact_golden_rejections"]),
        "high_similarity_review": len(coverage["high_similarity_review"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
