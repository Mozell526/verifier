from __future__ import annotations

from impl.core.judge import judge_trace as production_judge_trace
from impl.core.context.embedding import DeterministicHashEmbeddingProvider
from impl.core.project_loader import load_project
from impl.core.schema import RunTrace
from impl.projects.client_search.draft.judge import (
    _build_core_context as build_draft_context,
)
from impl.projects.client_search.draft.judge_execution import (
    judge_trace as draft_judge_trace,
)
from impl.projects.client_search.judge import (
    _build_core_context as build_production_context,
)


class _NoopJudgeLlm:
    model = "test-model"
    _project_id = "client_search"

    def __init__(self) -> None:
        self.tools = []
        self.system = ""

    def complete_json(self, system, _user, **_kwargs):
        self.system = system
        return {
            "business_expectations": [],
            "applicable_product_expectation_ids": [],
            "fulfillment_assessments": [],
            "expected": None,
            "missing": [],
            "wrong": [],
            "extra": [],
            "evidence": [],
            "reasoning_summary": "当前请求不属于客户搜索。",
        }


def _trace(trace_id: str) -> RunTrace:
    return RunTrace(
        trace_id=trace_id,
        project_id="client_search",
        input={"user_text": "你好"},
        normalized_request={"user_text": "你好"},
        extracted_output={},
        ready=["reference_contract_optional"],
    )


def test_production_compiler_records_clean_snapshot_and_slices_runtime_contract():
    spec = load_project("client_search")
    trace = _trace("context-governance-production")
    context = build_production_context(spec, trace)
    client = _NoopJudgeLlm()
    client.tools = list(context["tools"])

    production_judge_trace(
        spec,
        trace,
        llm=client,
        project_judge_context=context,
    )

    report = client._context_governance_report
    assert report["gate"] == {"mode": "production", "blocking": False}
    assert report["findings"] == []
    assert "`JudgeResult` 协议字段" not in client.system
    assert report["snapshot"]["excluded_segments"]
    assert report["snapshot"]["output_contract"]["sha256"]


def test_draft_compiler_blocks_nothing_when_contract_and_tool_plan_are_consistent():
    spec = load_project("client_search")
    trace = _trace("context-governance-draft")
    context = build_draft_context(
        spec,
        trace,
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    client = _NoopJudgeLlm()
    client.tools = list(context["tools"])

    draft_judge_trace(
        spec,
        trace,
        llm=client,
        project_judge_context=context,
    )

    report = client._context_governance_report
    assert report["gate"] == {"mode": "draft", "blocking": False}
    assert report["findings"] == []
    assert "`JudgeResult` 协议字段" not in client.system
    assert report["snapshot"]["tool_plan"]
