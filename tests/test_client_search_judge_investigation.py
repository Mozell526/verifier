from __future__ import annotations

import json

from impl.core.context.project import load_role_mandatory_context
from impl.core.context.embedding import DeterministicHashEmbeddingProvider
from impl.core.investigation import load_judge_solidify_investigation_projection
from impl.core.project_loader import load_project
from impl.core.schema import AuthorityResolution, RunTrace
from impl.projects.client_search.draft.probes.judge_solidify_probe import (
    FORBIDDEN_RUNTIME_FIELDS,
    build_probe_payload,
)


def _authority_spec():
    """Return the client_search spec with the authority runtime switch enabled.

    Draft Judge default (verifier.authority.enabled=false) disables authority;
    tests that exercise authority assembly/consumption must opt back in.
    """
    spec = load_project("client_search")
    authority = (spec.verifier or {}).setdefault("authority", {})
    authority["enabled"] = True
    return spec

def test_client_search_judge_solidify_projection_matches_smoke_evidence():
    spec = _authority_spec()
    runtime = load_judge_solidify_investigation_projection(
        spec, use_candidate=True
    )
    evidence = build_probe_payload()

    assert runtime["business_contract"]["business_expectations"][0]["expectation_id"] == (
        "find-target-customers"
    )
    # 新方案：调查交接=证据空间（business_contract + 权威调查报告），
    # runtime 不承载 authority 约束/决议资产，authority 判断现场 resolve。
    assert "authority" not in runtime
    assert FORBIDDEN_RUNTIME_FIELDS

    assert evidence["status"] == "succeeded"
    assert evidence["checks"]["authority_snapshot_sha256"]
    assert evidence["checks"]["report"]["materials"] == 11
    assert evidence["checks"]["report"]["coverage_gaps"] == 6
    authorities = evidence["checks"]["authorities"]
    assert {item["analysis_id"] for item in authorities.values()} == {
        "semantic-mapping-authority",
        "query-form-equivalence-authority",
        "responsibility-boundary-unsupported-field",
        "responsibility-boundary-entity-name-query",
        "silently-dropped-request-dimension",
        "enum-space-search-consumption-boundary",
    }
    assert all(item["dimension_ids"] for item in authorities.values())
    assert all(item["required_evidence"] for item in authorities.values())
    for check in authorities.values():
        assert check["case_time"] == {
            "without_decisive_evidence": "not_evaluable",
        }
def test_client_search_runtime_loads_solidified_authority_context_not_investigation_dump():
    spec = load_project("client_search")

    context = load_role_mandatory_context(
        spec,
        role="judge",
        operation="judge",
        trace_id="authority-context-test",
        run_id="authority-context-test",
    )

    assert context is not None
    assert "project.client_search.asset.judge_business_contract" in context["unit_ids"]
    assert "project.client_search.asset.judge_authority_enum_values" not in context["unit_ids"]
    assert not any("judge_investigation" in item for item in context["unit_ids"])
    assert "client_search.authority.enum-values" not in context["content"]


def test_client_search_builds_comparator_evidence_before_assessment(monkeypatch):
    """Draft 单次上下文：comparator 证据与 authority.resolve 工具一起进入同一会话。"""
    from impl.projects.client_search.draft import judge as candidate_module

    spec = _authority_spec()
    comparison = {
        "outputs": {
            "wrong": [],
            "missing": [{"field": "age"}],
            "extra": [],
        }
    }
    monkeypatch.setattr(candidate_module, "condition_comparison", lambda *_: comparison)

    context = candidate_module._build_core_context(
        spec,
        RunTrace(
            trace_id="trace-comparator",
            project_id="client_search",
            input={"query": "30岁以上女性客户"},
            extracted_output={"conditions": [{"field": "sex"}]},
        ),
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )

    assert context["comparator_result"] is comparison
    assert context["user_prompt_extras"]["condition_comparison"] == comparison
    authority_env = context["authority_environment"]
    assert authority_env.environment_snapshot_sha256
    assert context["environment_snapshot_sha256"] == (
        authority_env.environment_snapshot_sha256
    )
    tool_names = {getattr(tool, "name", "") for tool in context["tools"]}
    assert "authority_resolve" in tool_names
    assert "client_search_field_search_keys" in tool_names


def test_comparator_does_not_self_authorize():
    from impl.projects.client_search.draft.judge import condition_comparison

    comparison = condition_comparison(
        load_project("client_search"),
        RunTrace(
            trace_id="trace-current-oracle",
            project_id="client_search",
            input={"query": "帮我找高净值客户"},
            reference_contract={
                "oracle": "current",
                "expected_conditions": [
                    {
                        "field": "clientLevel",
                        "operator": "eq",
                        "value": "VIP",
                    }
                ],
            },
            extracted_output={
                "query_logic": "AND",
                "conditions": [
                    {
                        "field": "clientLevel",
                        "operator": "eq",
                        "value": "VIP",
                    }
                ],
            },
            ready=["reference"],
        ),
    )

    assert comparison["status"] == "succeeded"
    assert comparison["outputs"]["evaluable"] is True
    assert "authority_resolutions" not in comparison["outputs"]


def test_non_oracle_reference_is_evidence_only_not_a_comparison_standard():
    from impl.projects.client_search.draft.judge import condition_comparison

    comparison = condition_comparison(
        load_project("client_search"),
        RunTrace(
            trace_id="trace-historical-reference",
            project_id="client_search",
            input={"query": "帮我找高净值客户"},
            reference_contract={
                "oracle": "historical",
                "expected_conditions": [{
                    "field": "clientLevel",
                    "operator": "eq",
                    "value": "VIP",
                }],
            },
            extracted_output={
                "conditions": [{
                    "field": "clientLevel",
                    "operator": "eq",
                    "value": "OTHER",
                }]
            },
            ready=["reference"],
        ),
    )

    outputs = comparison["outputs"]
    assert outputs["expected_source"] == "reference_evidence"
    assert outputs["evaluable"] is False
    assert outputs["wrong"] == []
    assert outputs["missing"] == []
    assert outputs["extra"] == []
    assert "authority_resolutions" not in outputs


def test_comparator_cannot_use_reference_without_trace_readiness():
    from impl.projects.client_search.draft.judge import condition_comparison

    comparison = condition_comparison(
        load_project("client_search"),
        RunTrace(
            trace_id="trace-reference-not-ready",
            project_id="client_search",
            input={"query": "帮我找高净值客户"},
            reference_contract={
                "oracle": "current",
                "expected_conditions": [{
                    "field": "clientLevel",
                    "operator": "eq",
                    "value": "VIP",
                }],
            },
            extracted_output={
                "conditions": [{
                    "field": "clientLevel",
                    "operator": "eq",
                    "value": "VIP",
                }]
            },
            ready=[],
        ),
    )

    assert comparison["outputs"]["evaluable"] is False
    assert "authority_resolutions" not in comparison["outputs"]


def _seed_authority_audit(
    authority_tool,
    call_id: str,
    *,
    status: str,
    reason: str,
    unit_id: str = "ref-a",
    required_evidence: tuple[str, ...] = (),
) -> None:
    authority_tool.audit[call_id] = {
        "request": {"decision_question": "当前判断必须采用哪个业务定义？"},
        "resolution": AuthorityResolution(
            status=status,
            statement="" if status == "unresolved" else "采用当前正式定义。",
            reason=reason,
            basis_evidence_ref_ids=(unit_id,),
            required_evidence=tuple(required_evidence),
        ),
        "environment_snapshot_sha256": authority_tool._env.environment_snapshot_sha256,
    }


class SinglePassJudgeLlm:
    def __init__(self, data):
        self.data = data
        self.calls = 0
        self.call_kwargs = []
        self._caller = "judge"

    def complete_json(self, *_args, **_kwargs):
        self.calls += 1
        self.call_kwargs.append(dict(_kwargs))
        return dict(self.data)


def test_client_search_runtime_applies_traceable_authority_gate():
    """§8：单次 agentic 会话内 authority.resolve 的 Tool audit 被 Core 后处理消费。

    unresolved 的引用 → 依赖 assessment 转 not_evaluable；无关 assessment 不阻断；
    authority_runtime 审计证据写入 result.evidence。
    """
    from impl.projects.client_search.draft import judge as candidate_module
    from impl.projects.client_search.draft.judge_execution import judge_trace

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="trace-authority-runtime",
        project_id="client_search",
        input={"query": "帮我找高净值客户"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [
                {"field": "vipType", "operator": "eq", "value": "VIP"}
            ],
        },
        status="ok",
    )
    context = candidate_module._build_core_context(
        spec, trace, embedding_provider=DeterministicHashEmbeddingProvider()
    )
    authority_tool = context["authority_tool"]
    _seed_authority_audit(
        authority_tool,
        "tc-semantic",
        status="unresolved",
        reason=(
            "产品术语资料与历史案例来自不同治理链路，"
            "当前无法确认正式采用哪套定义。"
        ),
        required_evidence=("正式定义来源与生效版本",),
    )
    client = SinglePassJudgeLlm({
        "business_expectations": [
            {
                "expectation_id": "explicit-condition",
                "blocking": True,
                "expected_outcome": "明确条件不得遗漏",
                "acceptance_criteria": ["明确条件不得遗漏"],
            },
            {
                "expectation_id": "semantic-mapping",
                "blocking": True,
                "expected_outcome": "语义映射必须有权威依据",
                "acceptance_criteria": ["语义映射必须有权威依据"],
            },
        ],
        "fulfillment_assessments": [
            {
                "expectation_id": "explicit-condition",
                "status": "fulfilled",
            },
            {
                "expectation_id": "semantic-mapping",
                "status": "fulfilled",
                "authority_tool_call_ids": ["tc-semantic"],
            },
        ],
        "expected": {
            "query_logic": "AND",
            "conditions": [
                {"field": "vipType", "operator": "eq", "value": "VIP"}
            ],
        },
        "reasoning_summary": "初始评估",
    })

    result = judge_trace(
        spec,
        trace,
        user_intent="帮我找高净值客户",
        llm=client,
        project_judge_context=context,
    )

    assert client.calls == 1
    assert client.call_kwargs[0]["stage"] == "judge"
    assert "tools_override" not in client.call_kwargs[0]

    assessments = {
        item.expectation_id: item for item in result.fulfillment_assessments
    }
    assert assessments["explicit-condition"].status == "fulfilled"
    semantic = assessments["semantic-mapping"]
    assert semantic.status == "not_evaluable"
    entry = next(
        item
        for item in semantic.evidence_refs
        if isinstance(item, dict) and item.get("kind") == "authority_unresolved"
    )
    assert entry["reason"]
    assert entry["required_evidence"] == ["正式定义来源与生效版本"]
    assert entry["environment_snapshot_sha256"] == (
        authority_tool._env.environment_snapshot_sha256
    )
    runtime_audit = next(
        item
        for item in result.evidence
        if isinstance(item, dict) and item.get("source") == "authority_runtime"
    )
    assert runtime_audit["tool_call_ids"] == ["tc-semantic"]


def test_client_search_judge_reference_missing_tool_call_marks_needs_human_review():
    """§8：assessment 引用了 audit 中不存在的 tool_call_id → needs_human_review，不静默放行。"""
    from impl.projects.client_search.draft import judge as candidate_module
    from impl.projects.client_search.draft.judge_execution import judge_trace

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="trace-authority-missing-ref",
        project_id="client_search",
        input={"query": "帮我找高净值客户"},
        extracted_output={
            "conditions": [
                {"field": "vipType", "operator": "eq", "value": "VIP"}
            ],
        },
        status="ok",
    )
    context = candidate_module._build_core_context(
        spec, trace, embedding_provider=DeterministicHashEmbeddingProvider()
    )
    client = SinglePassJudgeLlm({
        "business_expectations": [
            {
                "expectation_id": "semantic-mapping",
                "blocking": True,
                "expected_outcome": "语义映射必须有权威依据",
                "acceptance_criteria": ["语义映射必须有权威依据"],
            },
        ],
        "fulfillment_assessments": [
            {
                "expectation_id": "semantic-mapping",
                "status": "fulfilled",
                "authority_tool_call_ids": ["tc-never-ran"],
            },
        ],
        "expected": {
            "query_logic": "AND",
            "conditions": [
                {"field": "vipType", "operator": "eq", "value": "VIP"}
            ],
        },
        "reasoning_summary": "引用了一次未发生的 Authority 调用",
    })

    result = judge_trace(
        spec,
        trace,
        user_intent="帮我找高净值客户",
        llm=client,
        project_judge_context=context,
    )

    assessment = result.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    marker = next(
        item
        for item in assessment.evidence_refs
        if isinstance(item, dict)
        and item.get("kind") == "authority_reference_missing"
    )
    assert marker["needs_human_review"] is True


def test_candidate_accepts_live_request_user_text_as_pre_actual_intent():
    from impl.projects.client_search.draft.judge import build_intent_frame

    spec = load_project("client_search")
    intent_frame = build_intent_frame(
        spec,
        RunTrace(
            trace_id="applicability:user-text",
            project_id="client_search",
            input={"user_text": "查找30岁以上的客户"},
            normalized_request={"user_text": "查找30岁以上的客户"},
        ),
    )

    assert intent_frame["request_candidates"] == [
        {
            "source": "normalized_request.user_text",
            "value": "查找30岁以上的客户",
        },
        {
            "source": "input.user_text",
            "value": "查找30岁以上的客户",
        },
    ]


def test_candidate_field_key_tool_returns_only_short_candidates():
    from impl.projects.client_search.draft.field_tools import search_field_key_index
    from impl.projects.client_search.draft.judge import _build_judge_tools

    spec = load_project("client_search")
    candidates = search_field_key_index(spec, "17、18周岁的客户")

    assert candidates
    assert candidates[0]["field"] == "clientAge"
    assert candidates[0]["short_name"] == "客户本人年龄"
    assert set(candidates[0]) == {"field", "short_name"}
    assert all(len(str(item["short_name"])) <= 32 for item in candidates)

    assert search_field_key_index(spec, "十里堡") == []

    tools = _build_judge_tools(spec)
    assert {tool.name for tool in tools} == {
        "client_search_field_search_keys",
        "field_search_definition",
    }
    key_tool = next(
        tool
        for tool in tools
        if tool.name == "client_search_field_search_keys"
    )
    definition_tool = next(
        tool
        for tool in tools
        if tool.name == "field_search_definition"
    )
    assert len(key_tool.description) < 200
    assert len(json.dumps(key_tool.parameters, ensure_ascii=False)) < 600

    definition = definition_tool.entrypoint(field="clientAge")
    assert set(definition.actual) == {
        "field",
        "operators",
        "value_types",
        "is_supported",
        "short_name",
        "unit",
    }
    assert definition.actual["field"] == "clientAge"
    assert definition.actual["is_supported"] is True
    assert "description" not in definition.actual
    assert "examples" not in definition.actual
    assert "notes" not in definition.actual


def test_candidate_context_is_small_and_rejects_unrelated_request():
    from impl.projects.client_search.draft.judge import _build_core_context

    context = _build_core_context(
        _authority_spec(),
        RunTrace(
            trace_id="applicability:weather",
            project_id="client_search",
            input={"query": "今天天气怎么样"},
            normalized_request={"query": "今天天气怎么样"},
        ),
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )

    assert "applicable_product_expectation_ids" not in context
    assert context["authority_environment"].environment_snapshot_sha256
    assert context["environment_snapshot_sha256"] == (
        context["authority_environment"].environment_snapshot_sha256
    )
    extras = context["user_prompt_extras"]
    assert extras["product_use_scenarios"]["find-target-customers"]
    assert extras["capability_manifest"] == {}
    assert extras["value_mappings"] == {}
    assert set(extras["enhanced_rules"]) <= {"negation_words"}
    assert "condition_comparison" in extras
    tool_names = {getattr(tool, "name", "") for tool in context["tools"]}
    assert "authority_resolve" in tool_names
    joined = "\n".join(context["system_prompt_extras"])
    assert "fulfillment_assessments 字段约束" in joined
    assert "authority.resolve" in joined
    assert "authority_tool_call_ids" in joined


def test_judge_context_injects_evidence_space_not_curated_conclusions():
    """新方案：调查交接=证据空间（报告），不给 runtime 预置"问题→结论"决议。

    上下文不再注入 judge_authority_resolutions / authority_reuse_records；
    authority 判断由 Judge 现场调用 authority.resolve 在物化证据空间内裁决。
    """
    from impl.projects.client_search.draft.judge import (
        _build_core_context,
        _load_authority_report,
    )

    spec = _authority_spec()
    report = _load_authority_report(spec)
    assert len(report.materials) == 11
    gap_ids = {gap.gap_id for gap in report.coverage_gaps}
    assert gap_ids == {
        "semantic-mapping-authority",
        "query-form-equivalence-authority",
        "responsibility-boundary-unsupported-field",
        "responsibility-boundary-entity-name-query",
        "silently-dropped-request-dimension",
        "enum-space-search-consumption-boundary",
    }
    assert all(gap.required_evidence for gap in report.coverage_gaps)

    context = _build_core_context(
        spec,
        RunTrace(
            trace_id="evidence-space-not-resolutions",
            project_id="client_search",
            input={"query": "贵C826N1"},
            normalized_request={"query": "贵C826N1"},
        ),
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    extras = context["user_prompt_extras"]
    assert "judge_authority_resolutions" not in extras
    assert "authority_reuse_records" not in context
    assert context["authority_environment"].environment_snapshot_sha256
    tool_names = {getattr(tool, "name", "") for tool in context["tools"]}
    assert "authority_resolve" in tool_names


def test_single_pass_judge_consumes_unresolved_authority_resolutions():
    """§8：单次会话内多个 unresolved authority.resolve 分别转对应 assessment 为 not_evaluable。"""
    from impl.projects.client_search.draft import judge as candidate_module
    from impl.projects.client_search.draft.judge_execution import judge_trace

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="authority:explicit-home-cue",
        project_id="client_search",
        input={"query": "平安居家V1及以上客户"},
        normalized_request={"query": "平安居家V1及以上客户"},
        extracted_output={
            "query": "平安居家V1及以上客户",
            "conditions": [{
                "field": "pajjMemberGradeInfo.pajjmembergradesearch",
                "operator": "MATCH",
                "value": "平安居家V1及以上",
            }],
            "query_logic": "AND",
        },
        status="ok",
    )
    context = candidate_module._build_core_context(
        spec, trace, embedding_provider=DeterministicHashEmbeddingProvider()
    )
    authority_tool = context["authority_tool"]
    _seed_authority_audit(
        authority_tool,
        "tc-semantic",
        status="unresolved",
        reason="平安居家V1及以上目标的正式业务值存在两套定义冲突（V1优享/V1及以上的边界）。",
        required_evidence=("正式定义来源",),
    )
    _seed_authority_audit(
        authority_tool,
        "tc-enum",
        status="unresolved",
        reason="pajjMemberGradeInfo.pajjmembergradesearch 的合法值全集缺少下游权威导出。",
        required_evidence=("只读下游聚合",),
    )
    client = SinglePassJudgeLlm({
        "business_expectations": [
            {
                "expectation_id": "home-boundary",
                "blocking": True,
                "expected_outcome": "把平安居家V1及以上映射到pajjMemberGradeInfo.pajjmembergradesearch中的正确业务值",
                "acceptance_criteria": ["保留平安居家等级语义"],
            },
            {
                "expectation_id": "home-enum",
                "blocking": True,
                "expected_outcome": "pajjMemberGradeInfo.pajjmembergradesearch使用下游合法枚举值",
                "acceptance_criteria": ["枚举值完整覆盖业务类别"],
            },
        ],
        "fulfillment_assessments": [
            {
                "expectation_id": "home-boundary",
                "status": "not_evaluable",
                "authority_tool_call_ids": ["tc-semantic"],
            },
            {
                "expectation_id": "home-enum",
                "status": "not_evaluable",
                "authority_tool_call_ids": ["tc-enum"],
            },
        ],
        "expected": {
            "query_logic": "AND",
            "conditions": [
                {"field": "pajjMemberGradeInfo.pajjmembergradesearch", "operator": "MATCH"}
            ],
        },
        "reasoning_summary": "两个不同判断点分别缺少决定性证据",
    })

    result = judge_trace(
        spec,
        trace,
        user_intent="平安居家V1及以上客户",
        llm=client,
        project_judge_context=context,
    )

    assert client.calls == 1
    assert result.overall_fulfillment["status"] == "not_evaluable"
    by_id = {item.expectation_id: item for item in result.fulfillment_assessments}
    assert by_id["home-boundary"].status == "not_evaluable"
    assert by_id["home-enum"].status == "not_evaluable"
    assert {
        tuple(item.authority_tool_call_ids)
        for item in result.fulfillment_assessments
    } == {("tc-semantic",), ("tc-enum",)}
    assert "planning failed" not in result.reasoning_summary


def test_single_pass_judge_uses_resolved_authority_without_override():
    """§8：resolution=resolved 时不覆盖 Judge 结论，assessment 保持原判定。"""
    from impl.projects.client_search.draft import judge as candidate_module
    from impl.projects.client_search.draft.judge_execution import judge_trace

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="authority:enum-completeness",
        project_id="client_search",
        input={"query": "剔除某业务类别客户"},
        normalized_request={"query": "剔除某业务类别客户"},
        extracted_output={"conditions": []},
        status="ok",
    )
    context = candidate_module._build_core_context(
        spec, trace, embedding_provider=DeterministicHashEmbeddingProvider()
    )
    authority_tool = context["authority_tool"]
    _seed_authority_audit(
        authority_tool,
        "tc-enum",
        status="resolved",
        reason="下游只读聚合唯一决定合法值全集。",
    )
    client = SinglePassJudgeLlm({
        "business_expectations": [
            {
                "expectation_id": "exclude-category",
                "blocking": True,
                "expected_outcome": "排除完整业务类别",
                "acceptance_criteria": ["值覆盖产品枚举中的所有产品简称"],
            },
        ],
        "fulfillment_assessments": [
            {
                "expectation_id": "exclude-category",
                "status": "fulfilled",
                "authority_tool_call_ids": ["tc-enum"],
                "actual_evidence": ["actual 列表与下游合法值全集一致"],
            },
        ],
        "reasoning_summary": "已确认合法值全集，排除列表完整。",
    })

    result = judge_trace(
        spec,
        trace,
        user_intent="剔除某业务类别客户",
        llm=client,
        project_judge_context=context,
    )

    assessment = result.fulfillment_assessments[0]
    assert assessment.status == "fulfilled"
    assert assessment.authority_tool_call_ids == ["tc-enum"]


def test_candidate_reports_unrelated_request_as_not_applicable(monkeypatch):
    """适用性判断交回单次 Judge LLM：不适用时 LLM 输出空 business_expectations。"""
    from impl.core import llm_client as llm_client_module
    from impl.projects.client_search.draft import judge as candidate_module
    from impl.projects.client_search.draft.judge import ClientSearchJudge
    from impl.core.authority_environment import build_authority_environment as real_build

    def _test_build(
        spec,
        *,
        role="judge",
        use_candidate=True,
        gateway_tools=(),
        embedding_provider=None,
        trace_id="",
        case_id="",
        business_source_staleness_policy="warn",
    ):
        return real_build(
            spec,
            role=role,
            use_candidate=use_candidate,
            gateway_tools=gateway_tools,
            embedding_provider=DeterministicHashEmbeddingProvider(),
            trace_id=trace_id,
            case_id=case_id,
            business_source_staleness_policy=business_source_staleness_policy,
        )

    monkeypatch.setattr(candidate_module, "build_authority_environment", _test_build)

    class NotApplicableLlm:
        def __init__(self):
            self.calls = 0

        def complete_json(self, *_args, **_kwargs):
            self.calls += 1
            return {
                "business_expectations": [],
                "fulfillment_assessments": [],
                "reasoning_summary": (
                    "该请求是天气查询，不属于 find-target-customers 客户搜索场景，"
                    "业务不适用。"
                ),
            }

    client = NotApplicableLlm()
    monkeypatch.setattr(
        llm_client_module,
        "project_llm_client",
        lambda *_args, **_kwargs: client,
    )

    result = ClientSearchJudge(load_project("client_search")).judge_trace(
        RunTrace(
            trace_id="applicability:weather-result",
            project_id="client_search",
            input={"query": "今天天气怎么样"},
            normalized_request={"query": "今天天气怎么样"},
            extracted_output={"answer": "晴"},
            status="ok",
        )
    )

    assert client.calls == 1
    assert result.overall_fulfillment["status"] == "not_evaluable"
    assert result.business_expectations == []
    assert result.fulfillment_assessments == []
    assert "不适用" in result.reasoning_summary
    assert "LLM 调用失败" not in result.reasoning_summary
    assert {
        "source": "business_expectation_applicability",
        "status": "not_applicable",
        "cause": "完全无关",
        "trace_id": "applicability:weather-result",
    } in result.evidence


def test_judge_prompt_contract_requires_not_evaluable_cause_markers():
    """上下文工程：judge prompt 必须指示 not_evaluable 成因标签契约。

    authority_gate §8.4 只消费显式「结论类型：」标记；prompt 不指示则 LLM 不会写，
    导致输入坏/完全无关等豁免成因也被标 needs_human_review（噪音人审）。
    """
    from impl.projects.client_search.draft import judge as candidate_module

    spec = load_project("client_search")
    trace = RunTrace(
        trace_id="contract:ne-cause-marker",
        project_id="client_search",
        input={"query": "30岁女性客户"},
        normalized_request={"query": "30岁女性客户"},
        extracted_output={
            "conditions": [
                {"field": "age", "operator": "MATCH", "value": 30},
                {"field": "sex", "operator": "MATCH", "value": "女"},
            ],
        },
    )
    ctx = candidate_module._build_core_context(spec, trace)
    joined = "\n".join(ctx["system_prompt_extras"])
    assert "结论类型：职责外" in joined
    assert "结论类型：完全无关" in joined
    assert "结论类型：依据不充分" in joined
    assert "结论类型：输入坏" in joined
    assert "缺料清单" in joined


def test_candidate_judge_tool_reuses_same_audited_result_for_duplicate_arguments(
    monkeypatch,
):
    from impl.projects.client_search.draft import judge as candidate_module
    from impl.tools import ToolResult, VerifiableTool

    calls = []

    def execute(*, field):
        calls.append(field)
        return ToolResult(
            tool_id="field.search_definition",
            tool_type="field_retrieval",
            outputs={"field": field},
        )

    monkeypatch.setattr(candidate_module, "load_field_provider", lambda _spec: object())
    monkeypatch.setattr(
        candidate_module,
        "create_minimal_field_definition_tool",
        lambda _provider, _registry=None: VerifiableTool(
            tool_id="field.search_definition",
            description="查找字段定义",
            parameters={
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "字段名",
                    }
                },
                "required": ["field"],
            },
            execute_fn=execute,
        ),
    )

    function = next(
        item
        for item in candidate_module._build_judge_tools(load_project("client_search"))
        if item.name == "field_search_definition"
    )
    first = function.entrypoint(field="clientAge")
    second = function.entrypoint(field="clientAge")
    third = function.entrypoint(field="clientCity")

    assert first.outputs == second.outputs
    assert third.outputs["field"] == "clientCity"
    assert calls == ["clientAge", "clientCity"]


def test_operator_justified_enum_exact_match_gate():
    """MATCH→CONTAINS 收敛：单值精确命中清单枚举才放行，清单外值/多值/字典不放行。"""
    from impl.projects.client_search.draft.judge import _operator_justified

    entry = {
        "operators": ["CONTAINS", "EXISTS", "NOT_CONTAINS", "NOT_EXISTS"],
        "value_types": ["enum", "exists", "not_exists"],
        "enums": [
            "车辆交强险", "车辆商业险", "e生保", "中高端医疗", "合家欢",
            "家财险", "学平险", "财富", "健康", "生活",
        ],
    }
    assert _operator_justified("agentPerspProductType", "MATCH", entry, [], value="合家欢")
    assert not _operator_justified("agentPerspProductType", "MATCH", entry, [], value="合家福")
    assert not _operator_justified(
        "agentPerspProductType", "MATCH", entry, [], value=["合家欢", "健康"]
    )
    assert not _operator_justified(
        "agentPerspProductType", "MATCH", entry, [], value={"min": "a", "max": "b"}
    )
    assert _operator_justified("agentPerspProductType", "CONTAINS", entry, [], value=["合家欢"])


def test_operator_justified_range_family_and_equivalence_rules():
    """范围族互容与显式等价规则仍放行，不依赖枚举命中。"""
    from impl.projects.client_search.draft.judge import _operator_justified

    age_entry = {
        "operators": ["EXISTS", "GTE", "LTE", "NOT_EXISTS", "RANGE"],
        "value_types": ["exists", "numeric"],
        "enums": [],
    }
    assert _operator_justified("clientAge", "RANGE", age_entry, [], value={"min": 18, "max": 30})
    assert _operator_justified("clientAge", "GT", age_entry, [], value=30)
    rule = {"field": "clientAge", "operator": "BETWEEN"}
    assert _operator_justified("clientAge", "BETWEEN", age_entry, [rule], value={"min": 1, "max": 2})


def test_operator_capability_check_defers_conflict_field():
    """Authority 开启时，operator 冲突缺少裁决引用会 fail-closed 为 NE。

    决议#4（unresolved，观察）声明该字段 MATCH 定义与 RANGE 示例冲突，实际可执行
    操作符无法由资料唯一确定 → 留给 authority.resolve 现场裁决。
    """
    from impl.projects.client_search.draft.judge import _apply_operator_capability_check
    from impl.core.schema import FulfillmentAssessment, JudgeResult, RunTrace

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="operator-gate-023",
        project_id="client_search",
        input={"query": "少儿万能险且有子女"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [
                {"field": "pTypes", "operator": "MATCH", "value": "万能型"},
                {"field": "familyInfo.familyrelation", "operator": "MATCH", "value": "子女"},
                {
                    "field": "familyInfo.familyclientbirthday",
                    "operator": "NOT_MATCH",
                    "value": {"min": "2008-07-29 00:00:00", "max": "2026-07-28 23:59:59"},
                },
            ],
        },
    )
    result = JudgeResult(trace_id="operator-gate-023", project_id="client_search")
    result.fulfillment_assessments = [
        FulfillmentAssessment(
            expectation_id="birthday-range",
            status="fulfilled",
            actual_evidence=[
                {
                    "field": "familyInfo.familyclientbirthday",
                    "operator": "NOT_MATCH",
                    "value": {"min": "2008-07-29 00:00:00", "max": "2026-07-28 23:59:59"},
                }
            ],
        )
    ]
    _apply_operator_capability_check(spec, trace, result)

    assessment = result.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    marker = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "operator_authority_required_not_consulted"
    )
    assert marker["needs_human_review"] is True
    assert any(
        item.get("source") == "capability_manifest.operator_conflict_deferred"
        and "familyInfo.familyclientbirthday" in str(item.get("fields"))
        for item in result.evidence
    )
    violation = next(
        item for item in result.evidence
        if item.get("source") == "capability_manifest.operator_violation"
    )
    assert "familyInfo.familyclientbirthday" in str(violation["violations"])
    assert "not by itself proof" in violation["rule"]


def test_operator_capability_check_does_not_override_judge_when_authority_disabled():
    """Authority 关闭时，capability mismatch 不得覆盖 Judge 的 F/NF。"""
    from impl.core.project_loader import load_project
    from impl.projects.client_search.draft.judge import _apply_operator_capability_check
    from impl.core.schema import FulfillmentAssessment, JudgeResult, RunTrace

    spec = load_project("client_search")
    trace = RunTrace(
        trace_id="operator-gate-authority-required",
        project_id="client_search",
        input={"query": "30岁客户"},
        extracted_output={
            "conditions": [
                {"field": "clientAge", "operator": "MATCH", "value": 30},
            ],
        },
    )
    result = JudgeResult(trace_id=trace.trace_id, project_id="client_search")
    result.fulfillment_assessments = [
        FulfillmentAssessment(
            expectation_id="age-filter",
            status="fulfilled",
            actual_evidence=[{"detail": "clientAge 使用 MATCH"}],
        )
    ]

    _apply_operator_capability_check(spec, trace, result)

    assessment = result.fulfillment_assessments[0]
    assert assessment.status == "fulfilled"
    assert assessment.score is None
    assert assessment.downstream_impact == ""
    assert not assessment.evidence_refs
    assert not result.evidence


def test_operator_capability_check_accepts_family_birthday_range_forms():
    from impl.core.project_loader import load_project
    from impl.projects.client_search.draft.judge import _actual_operator_violations
    from impl.core.schema import RunTrace

    spec = load_project("client_search")
    for operator, value in [
        ("GTE", "2020-08-12 00:00:00"),
        ("LTE", "2008-08-11 23:59:59"),
        ("RANGE", {"min": "2013-08-12 00:00:00", "max": "2020-08-11 23:59:59"}),
    ]:
        trace = RunTrace(
            trace_id=f"family-birthday-{operator.lower()}",
            project_id="client_search",
            input={"query": "家庭成员年龄条件"},
            extracted_output={
                "conditions": [{
                    "field": "familyInfo.familyclientbirthday",
                    "operator": operator,
                    "value": value,
                }],
            },
        )
        assert _actual_operator_violations(spec, trace) == []


def test_operator_capability_check_does_not_penalize_unrelated_assessment():
    from impl.core.project_loader import load_project
    from impl.projects.client_search.draft.judge import _apply_operator_capability_check
    from impl.core.schema import FulfillmentAssessment, JudgeResult, RunTrace

    spec = load_project("client_search")
    trace = RunTrace(
        trace_id="operator-gate-unrelated-assessment",
        project_id="client_search",
        input={"query": "30岁客户"},
        extracted_output={
            "conditions": [{"field": "clientAge", "operator": "MATCH", "value": 30}],
        },
    )
    result = JudgeResult(trace_id=trace.trace_id, project_id="client_search")
    result.fulfillment_assessments = [
        FulfillmentAssessment(
            expectation_id="age-filter",
            status="fulfilled",
            score=1.0,
            actual_evidence=[{"field": "clientAge", "operator": "MATCH", "value": 30}],
        ),
        FulfillmentAssessment(
            expectation_id="no-extra-constraints",
            status="fulfilled",
            score=1.0,
            actual_evidence=[{"fields": ["clientAge"], "conditions_count": 1}],
        ),
    ]

    _apply_operator_capability_check(spec, trace, result)

    assert result.fulfillment_assessments[0].status == "fulfilled"
    assert result.fulfillment_assessments[1].status == "fulfilled"


def test_operator_capability_check_preserves_semantic_equivalence_without_authority(
    monkeypatch,
):
    from impl.core.project_loader import load_project
    from impl.projects.client_search.draft import judge as judge_module
    from impl.core.schema import FulfillmentAssessment, JudgeResult, RunTrace

    spec = load_project("client_search")
    trace = RunTrace(
        trace_id="operator-gate-family-age-equivalence",
        project_id="client_search",
        input={"query": "有6岁以下子女的客户"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [
                {
                    "field": "familyInfo.familyrelation",
                    "operator": "MATCH",
                    "value": "子女",
                },
                {
                    "field": "familyInfo.familyclientbirthday",
                    "operator": "GTE",
                    "value": "2020-08-12 00:00:00",
                },
            ],
        },
    )
    result = JudgeResult(trace_id=trace.trace_id, project_id="client_search")
    result.fulfillment_assessments = [
        FulfillmentAssessment(
            expectation_id="child-under-six",
            status="fulfilled",
            score=1.0,
            actual_evidence=[
                {
                    "field": "familyInfo.familyclientbirthday",
                    "operator": "GTE",
                    "value": "2020-08-12 00:00:00",
                }
            ],
        )
    ]
    monkeypatch.setattr(
        judge_module,
        "_actual_operator_violations",
        lambda _spec, _trace: [
            {
                "field": "familyInfo.familyclientbirthday",
                "operator": "GTE",
            }
        ],
    )

    judge_module._apply_operator_capability_check(spec, trace, result)

    assert result.fulfillment_assessments[0].status == "fulfilled"
    assert result.fulfillment_assessments[0].score == 1.0
    assert not result.evidence


def test_operator_capability_check_keeps_enum_exact_match():
    """单值 MATCH 精确命中清单枚举（128 形态）不被 operator gate 判不可执行。"""
    from impl.core.project_loader import load_project
    from impl.projects.client_search.draft.judge import _apply_operator_capability_check
    from impl.core.schema import FulfillmentAssessment, JudgeResult, RunTrace

    spec = load_project("client_search")
    trace = RunTrace(
        trace_id="operator-gate-128",
        project_id="client_search",
        input={"query": "合家福客户"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [
                {"field": "agentPerspProductType", "operator": "MATCH", "value": "合家欢"},
            ],
        },
    )
    result = JudgeResult(trace_id="operator-gate-128", project_id="client_search")
    result.fulfillment_assessments = [
        FulfillmentAssessment(
            expectation_id="product-match",
            status="fulfilled",
            actual_evidence=[{"detail": "agentPerspProductType MATCH 合家欢"}],
        )
    ]
    _apply_operator_capability_check(spec, trace, result)

    assert result.fulfillment_assessments[0].status == "fulfilled"
    assert not any(
        "capability_manifest.operator_violation" in str(item.get("source"))
        for item in result.evidence
    )




def test_candidate_skips_authority_environment_for_direct_evidence_case(monkeypatch):
    from impl.projects.client_search.draft import judge as candidate_module

    calls = []

    def _unexpected_build(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("direct-evidence case must not build Authority Environment")

    monkeypatch.setattr(candidate_module, "build_authority_environment", _unexpected_build)
    context = candidate_module._build_core_context(
        load_project("client_search"),
        RunTrace(
            trace_id="direct-evidence:no-authority",
            project_id="client_search",
            input={"query": "30岁女性客户"},
            normalized_request={"query": "30岁女性客户"},
            extracted_output={
                "query_logic": "AND",
                "conditions": [
                    {"field": "age", "operator": "MATCH", "value": 30},
                    {"field": "sex", "operator": "MATCH", "value": "女"},
                ],
            },
        ),
    )

    assert calls == []
    assert context["authority_environment"] is None
    assert context["authority_tool"] is None
    assert context["environment_snapshot_sha256"] == ""
    assert context["user_prompt_extras"]["authority_mode"] == "not_required"
    assert context["user_prompt_extras"]["authority_candidate_reasons"] == []
    assert "authority_resolve" not in {
        getattr(tool, "name", "") for tool in context["tools"]
    }


def test_disabled_authority_preserves_boundary_candidates_without_building_tool(monkeypatch):
    from impl.projects.client_search.draft import judge as candidate_module

    calls = []

    def _unexpected_build(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("disabled authority must not build Authority Environment")

    monkeypatch.setattr(candidate_module, "build_authority_environment", _unexpected_build)
    context = candidate_module._build_core_context(
        load_project("client_search"),
        RunTrace(
            trace_id="boundary:disabled-authority",
            project_id="client_search",
            input={"query": "7月盘客"},
            normalized_request={"query": "7月盘客"},
            extracted_output={
                "conditions": [],
                "robot_text": "提示：盘客暂不支持搜索，无法进行查询。",
            },
        ),
    )

    assert calls == []
    assert context["authority_environment"] is None
    assert context["authority_tool"] is None
    assert context["user_prompt_extras"]["authority_mode"] == "disabled_with_candidates"
    assert context["user_prompt_extras"]["authority_candidate_reasons"]
    prompt = "\n".join(context["system_prompt_extras"])
    assert "核心结果未交付或 blocking 维度缺失时判 not_fulfilled" in prompt
    assert "不得仅因 Authority 关闭或存在边界候选而判 not_evaluable" in prompt


def test_candidate_builds_authority_environment_for_boundary_candidate(monkeypatch):
    from impl.projects.client_search.draft import judge as candidate_module

    monkeypatch.setattr(
        candidate_module,
        "_unsupported_boundary_evidence",
        lambda _trace: {"all_conditions_unsupported": True},
    )
    context = candidate_module._build_core_context(
        _authority_spec(),
        RunTrace(
            trace_id="boundary:authority-required",
            project_id="client_search",
            input={"query": "按车牌找客户"},
            normalized_request={"query": "按车牌找客户"},
            extracted_output={"conditions": [], "robot_text": "暂不支持车牌查询"},
        ),
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )

    assert context["authority_environment"] is not None
    assert context["authority_tool"] is not None
    assert context["user_prompt_extras"]["authority_mode"] == "on_demand"
    assert (
        "capability_or_responsibility_boundary:all_conditions_unsupported"
        in context["user_prompt_extras"]["authority_candidate_reasons"]
    )


def test_candidate_triggers_on_explicit_unsupported_without_lexical_overlap():
    """093 类：请求是具体值、提示是字段标签，无词法重叠。

    Key-Index Search→Load 已把请求解析到 is_supported=false 字段
    （explicit_unsupported_capability=True）时，仍必须装配 authority：
    职责外/职责内能力缺失由 authority 现场裁决，不能静默落 not_evaluable
    （fulfilled.md §2.3 硬前提 1 / §10）。
    """
    from impl.projects.client_search.draft import judge as candidate_module

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="boundary:093-license-plate",
        project_id="client_search",
        input={"query": "贵C826N1"},
        normalized_request={"query": "贵C826N1"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [],
            "intent_summary": "提示：车牌号暂不支持搜索，无法进行查询。",
            "robot_text": "提示：车牌号暂不支持搜索，无法进行查询。",
        },
    )
    raw = candidate_module._unsupported_boundary_evidence(trace)
    assert raw.get("acknowledges_requested_constraint") is False
    enriched = candidate_module._enrich_unsupported_boundary_evidence(
        spec, trace, raw
    )
    assert enriched.get("explicit_unsupported_capability") is True

    context = candidate_module._build_core_context(
        spec,
        trace,
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    reasons = context["user_prompt_extras"]["authority_candidate_reasons"]
    assert context["user_prompt_extras"]["authority_mode"] == "on_demand"
    assert "capability_or_responsibility_boundary:explicit_unsupported_field" in reasons


def test_candidate_triggers_on_partial_acknowledged_unsupported():
    """073 类：系统保留部分条件但拒绝请求自身约束（部分不支持）。

    acknowledges_requested_constraint=True（约束标签与请求词法重叠）即视为
    能力边界判断点，即使不是 all_conditions_unsupported 也要装配 authority。
    """
    from impl.projects.client_search.draft import judge as candidate_module

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="boundary:073-policy-date",
        project_id="client_search",
        input={"query": "2025年6月份投保的新客户名单"},
        normalized_request={"query": "2025年6月份投保的新客户名单"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [
                {"field": "isBuyInsurance", "operator": "CONTAINS", "value": ["客户", "准客"]},
            ],
            "intent_summary": "客户类型包含客户、准客的客户\n提示：投保日期暂不支持搜索，系统将按可支持字段搜索。",
            "robot_text": "客户类型包含客户、准客的客户\n提示：投保日期暂不支持搜索，系统将按可支持字段搜索。",
        },
    )
    raw = candidate_module._unsupported_boundary_evidence(trace)
    assert raw.get("acknowledges_requested_constraint") is True
    assert raw.get("all_conditions_unsupported") is False

    context = candidate_module._build_core_context(
        spec,
        trace,
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    reasons = context["user_prompt_extras"]["authority_candidate_reasons"]
    assert context["user_prompt_extras"]["authority_mode"] == "on_demand"
    assert (
        "capability_or_responsibility_boundary:unsupported_constraint_acknowledged"
        in reasons
    )


def test_candidate_triggers_on_coverage_gap_for_silently_dropped_dimension():
    """138 类：请求维度被静默丢弃，无 notice/manifest 字段/reference 信号。

    请求文本命中调查层覆盖缺口（silently-dropped-request-dimension）且无更相关
    MaterialDecision 时，必须装配 authority：职责外/职责内能力缺失由 authority
    现场裁决（依赖调查层缺口索引，非启发式；investigate-authority-judge.md §11/§17）。
    """
    from impl.projects.client_search.draft import judge as candidate_module

    spec = _authority_spec()
    trace = RunTrace(
        trace_id="boundary:138-salesperson-dimension",
        project_id="client_search",
        input={"query": "陈金秀在别的业务员的投保的平安产品"},
        normalized_request={"query": "陈金秀在别的业务员的投保的平安产品"},
        extracted_output={
            "query_logic": "AND",
            "conditions": [
                {"field": "searchClientName", "operator": "MATCH", "value": "陈金秀"},
            ],
            "intent_summary": "客户姓名为陈金秀的客户",
            "robot_text": "客户姓名为陈金秀的客户",
        },
    )
    context = candidate_module._build_core_context(
        spec,
        trace,
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    reasons = context["user_prompt_extras"]["authority_candidate_reasons"]
    assert context["user_prompt_extras"]["authority_mode"] == "on_demand"
    assert (
        "capability_or_responsibility_boundary:coverage_gap:"
        "silently-dropped-request-dimension"
        in reasons
    )
    assert context["authority_environment"] is not None


def test_field_definition_tool_preserves_explicit_unsupported_flags():
    from impl.projects.client_search.draft.field_tools import (
        build_field_key_index_registry,
        create_minimal_field_definition_tool,
    )
    from impl.projects.client_search.field_provider import ClientSearchFieldDefinitionProvider

    spec = load_project("client_search")
    provider = ClientSearchFieldDefinitionProvider(spec)
    registry = build_field_key_index_registry(spec, provider)
    tool = create_minimal_field_definition_tool(provider, registry)

    for field in ("customerReview", "licensePlateNo"):
        result = tool.execute_fn(field=field)
        assert result.status == "succeeded"
        assert result.actual["is_supported"] is False
