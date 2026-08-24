from __future__ import annotations

import json
from dataclasses import replace

import pytest

from impl.core import llm_client
from impl.core import pipeline
from impl.core.context import project as context_project
from impl.core.context.embedding import DeterministicHashEmbeddingProvider
from impl.core.project_loader import (
    load_adapter,
    load_project,
    load_project_role_instance,
    load_project_role_tools,
)
from impl.core.interaction_protocol import normalize_case_interaction
from impl.core.mock import mock_case_to_single_turn, parse_mock_case
from impl.core.schema import to_dict
from impl.core.schema import MockBuildResult, SingleTurnCase
from impl.projects.deerflow.draft.tools.mock_validation_tools import (
    build_mock_business_input_validate_tool,
)
from impl.core.context.embedding import DeterministicHashEmbeddingProvider
from impl.core.context.project import load_role_mandatory_context
from impl.projects.deerflow.live_schema import MOCK_CASE_SEEDS
from impl.projects.deerflow.live import _stage_inference


def _case(scenario: str, intent: str, message: str) -> dict:
    return {
        "scenario": scenario,
        "user_intent": intent,
        "live_request": {
            "input": {"messages": [{"role": "user", "content": message}]},
            "config": {"configurable": {"thread_id": ""}},
        },
    }


def _mock_variant(enabled: bool):
    spec = load_project("deerflow")
    return _with_mock_draft(spec, enabled)


def _with_mock_draft(spec, enabled: bool = True):
    roles = dict(spec.verifier.get("roles") or {})
    mock_role = dict(roles.get("mock") or {})
    mock_role["draft"] = {
        **dict(mock_role.get("draft") or {}),
        "enabled": enabled,
        "module": "project://draft/mock.py",
    }
    roles["mock"] = mock_role
    return replace(spec, verifier={**spec.verifier, "roles": roles})


def test_deerflow_default_mock_switch_selects_complete_draft_bundle():
    spec = load_project("deerflow")

    implementation = load_project_role_instance(
        spec,
        "mock",
        load_adapter(spec),
    )
    context = load_role_mandatory_context(
        spec,
        role="mock",
        operation="mock",
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    tool_ids = {tool.tool_id for tool in load_project_role_tools(spec, "mock")}

    assert spec.role_draft("mock")["enabled"] is True
    assert type(implementation).__name__ == "DeerflowMockDraft"
    assert implementation.scenarios() == ["open_world_user"]
    assert context is not None
    assert context["unit_ids"] == ["project.deerflow.mock.business_contract"]
    assert "deerflow.mock_business_input_validate" in tool_ids


def test_deerflow_default_dynamic_pool_uses_active_draft_scenario(monkeypatch):
    scenarios = []

    def _build(_project_id, scenario="", **_kwargs):
        scenarios.append(scenario)
        return {
            "id": "draft-open-world",
            "project_id": "deerflow",
            "scenario": scenario,
            "intent": {
                "user_intent": "查看下月规划怎样调整更合适",
                "query": "下个月这版规划怎么调会更稳妥？",
                "user_context": {},
                "system_understanding": "",
                "scenario": scenario,
            },
            "live_request": {
                "input": {"messages": [{"role": "user", "content": "下个月这版规划怎么调会更稳妥？"}]},
                "config": {"configurable": {}},
            },
            "output": None,
            "reference": None,
        }

    monkeypatch.setattr(pipeline, "mock_build_intent", _build)

    cases = pipeline.generate_mock_cases("deerflow", count=1)

    assert scenarios == ["open_world_user"]
    assert cases[0]["scenario"] == "open_world_user"


def test_deerflow_mock_draft_loads_without_importing_production_role():
    spec = load_project("deerflow")
    draft_spec = _with_mock_draft(spec)

    implementation = load_project_role_instance(
        draft_spec,
        "mock",
        load_adapter(draft_spec),
    )

    assert type(implementation).__name__ == "DeerflowMockDraft"
    assert type(implementation).__mro__[1].__name__ == "DeerflowMockBase"
    assert implementation.intent_labels() == []

    normalized = implementation.normalize_case(
        SingleTurnCase(
            id="generated",
            scenario="single_turn_planning",
            user_intent="制定 NBEV 规划",
            input={
                "input": {"messages": [{"role": "user", "content": "制定 NBEV 规划"}]},
                "config": {
                    "configurable": {
                        "thread_id": "invented-thread",
                        "user_id": "invented-user",
                    }
                },
                "query": "legacy",
            },
        )
    )
    assert normalized.input["config"]["configurable"] == {}
    assert "query" not in normalized.input


def test_deerflow_mock_candidate_context_is_empty_in_current_and_loaded_in_draft():
    spec = _mock_variant(False)
    embedding = DeterministicHashEmbeddingProvider()

    assert load_role_mandatory_context(
        spec,
        role="mock",
        operation="mock",
        embedding_provider=embedding,
    ) is None

    draft_spec = _with_mock_draft(spec)
    context = load_role_mandatory_context(
        draft_spec,
        role="mock",
        operation="mock",
        embedding_provider=embedding,
    )

    assert context is not None
    assert context["unit_ids"] == ["project.deerflow.mock.business_contract"]
    assert "NBEV" in context["content"]


def test_deerflow_mock_draft_consumes_context_once_for_open_ended_intent(monkeypatch):
    calls = []

    class _Llm:
        def complete_json(self, system, _user, **_kwargs):
            calls.append((system, json.loads(_user)))
            return {
                "query": "我上次做到一半的方案还能接着弄吗？",
                "user_intent": "继续处理上次未完成的业务方案",
            }

    monkeypatch.setattr(llm_client, "project_llm_client", lambda *_args, **_kwargs: _Llm())
    spec = load_project("deerflow")
    draft_spec = _with_mock_draft(spec)
    implementation = load_project_role_instance(
        draft_spec,
        "mock",
        load_adapter(draft_spec),
    )

    intent = implementation.build_user_intent("open_world_user")

    assert intent.user_intent == "继续处理上次未完成的业务方案"
    assert len(calls) == 1
    assert "project.deerflow.mock.business_contract" in calls[0][0]
    assert "用户群体" in calls[0][0]
    assert calls[0][1]["template"]["generation_mode"] == "open_world_user_population"
    assert calls[0][1]["template"]["diversity_seed"]
    assert calls[0][1]["template"]["single_pass"] is True
    assert set(calls[0][1]["template"]["population_sample"]) == {
        "business_familiarity",
        "tool_familiarity",
        "expression",
        "current_state",
    }
    assert "纯产品支持问题" in calls[0][0]
    assert "合成月份、目标、进度" in calls[0][0]
    assert "每条必填槽位" in calls[0][0]


def test_deerflow_mock_candidate_validator_is_not_loaded_by_current():
    spec = _mock_variant(False)
    current_ids = {tool.tool_id for tool in load_project_role_tools(spec, "mock")}
    draft_spec = _with_mock_draft(spec)
    draft_ids = {tool.tool_id for tool in load_project_role_tools(draft_spec, "mock")}

    assert "deerflow.mock_business_input_validate" not in current_ids
    assert "deerflow.mock_business_input_validate" in draft_ids


def test_deerflow_draft_enables_only_candidate_mock_assets(monkeypatch):
    from impl.core.mock_agent import MockAgent

    captured = {}

    def _load_context(spec, **_kwargs):
        captured["spec"] = spec
        return {"content": "candidate NBEV business contract"}

    monkeypatch.setattr(context_project, "load_role_mandatory_context", _load_context)
    production_spec = _mock_variant(False)
    draft_spec = _with_mock_draft(production_spec)
    production = load_project_role_instance(
        production_spec,
        "mock",
        load_adapter(production_spec),
    )
    draft = load_project_role_instance(
        draft_spec,
        "mock",
        load_adapter(draft_spec),
    )

    production_mock_assets = [
        asset for asset in production.spec.asset_mappings() if "mock" in asset.roles
    ]
    draft_mock_assets = [
        asset for asset in draft.spec.asset_mappings() if "mock" in asset.roles
    ]
    assert production_mock_assets and all(asset.enabled for asset in production_mock_assets)
    assert draft_mock_assets and all(asset.enabled for asset in draft_mock_assets)
    from impl.core.project_loader import resolve_role_assets

    assert all(
        item["source"] == "production" and item["available"] is False
        for item in resolve_role_assets(production.spec, "mock", use_candidate=False)
    )
    assert all(
        item["source"] == "candidate"
        for item in resolve_role_assets(draft.spec, "mock", use_candidate=True)
    )
    assert MockAgent(draft.spec)._mandatory_context()["content"] == "candidate NBEV business contract"
    assert captured["spec"] is draft.spec


def test_deerflow_draft_loads_real_mock_business_context_without_changing_production():
    spec = _mock_variant(False)
    draft_spec = _with_mock_draft(spec)

    production_context = context_project.load_role_mandatory_context(
        spec,
        role="mock",
        operation="mock",
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )
    draft_context = context_project.load_role_mandatory_context(
        draft_spec,
        role="mock",
        operation="mock",
        embedding_provider=DeterministicHashEmbeddingProvider(),
    )

    assert production_context is None
    assert draft_context is not None
    assert draft_context["unit_ids"] == ["project.deerflow.mock.business_contract"]
    assert "DeerFlow 潜在用户群体与表达边界" in draft_context["content"]
    assert "不是一个标准" in draft_context["content"]


def test_draft_explicit_intent_is_single_pass_and_request_mapping_is_deterministic(monkeypatch):
    calls = []

    def _unexpected_context_load(*_args, **_kwargs):
        raise AssertionError("fixed requested_intent must not load project Context")

    monkeypatch.setattr(
        context_project,
        "load_role_mandatory_context",
        _unexpected_context_load,
    )

    class _IntentLlm:
        def complete_json(self, system, user, **kwargs):
            calls.append((system, user, kwargs))
            if '"requested_intent"' in user:
                payload = json.loads(user)
                assert payload["requested_intent"] == "机构内勤想调整现有方案中的一个产品明细，但没有说明调整值"
                assert payload["requested_intent"] not in payload["intent_labels"]
                assert payload["template"]["single_pass"] is True
                assert payload["template"]["generation_mode"] == "constrained_user_expression"
                assert "population_sample" not in payload["template"]
                assert "requested_intent 是调用方已经确定的具体用户目标" in system
                assert "泛指对象缩窄成某种具体类型或关系" in system
                assert "业务产品标识：deerflow。" in system
                assert load_project("deerflow").description not in system
                return {
                    "query": "现有方案里有个产品明细我想调一下，不过具体调多少还没定。",
                    "user_intent": "调整现有方案中的一个产品明细，但未确定调整值",
                    "user_context": {"role": "模型擅自补充的岗位"},
                    "system_understanding": "模型擅自补充的产品理解",
                }
            raise AssertionError("Draft DeerFlow request wrapping must not call LLM")

    monkeypatch.setattr(llm_client, "project_llm_client", lambda *_args, **_kwargs: _IntentLlm())
    spec = load_project("deerflow")
    draft_spec = _with_mock_draft(spec)
    implementation = load_project_role_instance(
        draft_spec,
        "mock",
        load_adapter(draft_spec),
    )

    case = implementation.generate_mock_case(
        scenario="clarification",
        intent="机构内勤想调整现有方案中的一个产品明细，但没有说明调整值",
    )

    assert len(calls) == 1
    assert case.input == {
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "现有方案里有个产品明细我想调一下，不过具体调多少还没定。",
                }
            ]
        },
        "config": {"configurable": {}},
    }
    assert case.user_intent == "机构内勤想调整现有方案中的一个产品明细，但没有说明调整值"
    assert "user_context" not in case.metadata
    assert case.metadata["mock_intent"]["user_context"] == {}
    assert case.metadata["mock_intent"]["system_understanding"] == ""
    assert case.metadata["schema_ok"] is True


def test_mock_validator_accepts_open_world_user_language_without_keyword_anchors():
    validate = build_mock_business_input_validate_tool().execute_fn
    valid = validate(
        case=_case(
            "single_turn_planning",
            "制定下月 NBEV 达成规划，从客户视角开始",
            "请从客户视角制定下月 NBEV 达成规划",
        )
    )
    open_world = validate(
        case=_case(
            "single_turn_planning",
            "继续处理之前没有完成的业务方案",
            "我上回做到一半的那个还能接着弄吗？",
        )
    )

    assert valid.actual["valid"] is True
    assert open_world.actual["valid"] is True

    inquiry = validate(
        case=_case(
            "single_turn_planning",
            "了解客户视角的 NBEV 含义",
            "请从客户视角解释 NBEV 是什么",
        )
    )
    assert inquiry.actual["valid"] is True

    internal_identifier = validate(
        case=_case(
            "single_turn_planning",
            "制定下月 NBEV 达成规划，从产品视角开始",
            "请调用 sales_forecast_v3 制定下月产品视角的 NBEV 达成规划",
        )
    )
    assert internal_identifier.actual["valid"] is False
    assert internal_identifier.actual["failures"] == ["system_internal_language"]


def test_validator_does_not_turn_scenario_labels_into_a_closed_semantic_taxonomy():
    result = build_mock_business_input_validate_tool().execute_fn(
        case=_case(
            "authorization_boundary",
            "查看另一个机构的月度 NBEV 方案",
            "请顺便展示另一个机构的月度 NBEV 方案",
        )
    )

    assert result.actual["valid"] is True
    assert result.actual["scenario"] == "authorization_boundary"

    mislabeled = build_mock_business_input_validate_tool().execute_fn(
        case=_case(
            "authorization_boundary",
            "制定本机构 NBEV 规划",
            "请制定本机构 NBEV 规划",
        )
    )
    assert mislabeled.actual["valid"] is True
    assert mislabeled.actual["failures"] == []


def test_deerflow_persisted_mock_pool_covers_business_scenarios():
    cases = pipeline._fixture_mock_cases("deerflow")
    validate = build_mock_business_input_validate_tool().execute_fn
    queries = []

    assert len(cases) == 6
    assert {case["scenario"] for case in cases} == {"open_world_user"}
    for case in cases:
        message = case["live_request"]["input"]["messages"][-1]["content"]
        queries.append(message)
        assert message == case["intent"]["query"]
        assert case["live_request"]["config"]["configurable"] == {}
        validation = validate(case={**case, "user_intent": case["intent"]["user_intent"]})
        assert validation.actual["valid"] is True
    assert len(set(queries)) == 6
    assert not any(
        marker in "\n".join(queries)
        for marker in ("天气", "翻译", "列车", "转圈", "打不开", "提交失败")
    )


def test_deerflow_multi_turn_scenario_uses_existing_interactive_runtime():
    stored_case = {
        "id": "deerflow-multi-turn-protocol-check",
        "project_id": "deerflow",
        "scenario": "multi_turn_dimension_accumulation",
        "intent": {
            "user_intent": "继续完成已开始的规划",
            "query": "再看看客户方面。",
            "user_context": {},
        },
        "live_request": {
            "input": {"messages": [{"role": "user", "content": "再看看客户方面。"}]},
            "config": {"configurable": {}},
        },
        "output": None,
        "reference": None,
    }
    runtime_case = to_dict(mock_case_to_single_turn(parse_mock_case(stored_case)))

    normalized = normalize_case_interaction("deerflow", runtime_case)

    assert normalized.mode == "interactive_intent"
    assert normalized.scenario == "multi_turn_dimension_accumulation"


def test_explicit_generation_uses_deerflow_business_seeds(monkeypatch):
    captured = []

    def _build(project_id, scenario="", requested_intent="", **_kwargs):
        from impl.projects.deerflow import live_schema

        resolved = requested_intent or live_schema.MOCK_CASE_SEEDS[scenario]["requested_intents"][0]
        captured.append((project_id, scenario, resolved))
        return {
            "id": f"generated-{scenario}",
            "project_id": project_id,
            "scenario": scenario,
            "intent": {"user_intent": resolved, "query": resolved, "user_context": {}},
            "live_request": {
                "input": {"messages": [{"role": "user", "content": resolved}]},
                "config": {"configurable": {}},
            },
            "output": None,
            "reference": None,
        }

    monkeypatch.setattr(pipeline, "mock_build_intent", _build)
    monkeypatch.setattr(pipeline, "load_project", lambda _project_id: _mock_variant(False))
    monkeypatch.setattr(pipeline.random, "sample", lambda population, k: population[:k])
    generated = pipeline.generate_mock_cases("deerflow", count=2)

    assert [case["scenario"] for case in generated] == [
        "single_turn_planning",
        "multi_turn_dimension_accumulation",
    ]
    assert all("NBEV" in requested_intent for _, _, requested_intent in captured)
    assert all(case["id"].startswith("generated-") for case in generated)


def test_deerflow_default_generation_excludes_non_agent_scenario(monkeypatch):
    sampled = {}

    def _sample(population, k):
        sampled["population"] = list(population)
        return list(population[:k])

    monkeypatch.setattr(pipeline.random, "sample", _sample)
    monkeypatch.setattr(
        pipeline,
        "mock_build_intent",
        lambda project_id, scenario="", **_kwargs: {
            "id": f"generated-{scenario}",
            "project_id": project_id,
            "scenario": scenario,
            "intent": {"user_intent": "NBEV 业务目标"},
            "live_request": {
                "input": {"messages": [{"role": "user", "content": "NBEV 业务目标"}]},
                "config": {"configurable": {}},
            },
            "output": None,
            "reference": None,
        },
    )

    pipeline.generate_mock_cases("deerflow", count=1)

    assert sampled["population"] == ["open_world_user"]


def test_deerflow_full_scenario_generation_retains_non_agent_scenario(monkeypatch):
    generated_scenarios = []

    def _build(project_id, scenario="", **_kwargs):
        generated_scenarios.append(scenario)
        return {
            "id": f"generated-{scenario}",
            "project_id": project_id,
            "scenario": scenario,
            "intent": {"user_intent": "边界测试目标"},
            "live_request": {
                "input": {"messages": [{"role": "user", "content": "边界测试目标"}]},
                "config": {"configurable": {}},
            },
            "output": None,
            "reference": None,
        }

    monkeypatch.setattr(pipeline, "mock_build_intent", _build)

    pipeline.generate_mock_cases("deerflow", cases_per_scenario=1)

    assert "non_agent_intent" in generated_scenarios


def test_explicit_generation_rejects_empty_llm_result(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "mock_build_intent",
        lambda *_args, **_kwargs: {
            "id": "empty",
            "project_id": "deerflow",
            "scenario": "single_turn_planning",
            "intent": {"user_intent": "", "query": "", "user_context": {}},
            "live_request": {"input": "", "config": ""},
            "output": None,
            "reference": None,
        },
    )

    try:
        pipeline.generate_mock_cases("deerflow", count=1)
    except RuntimeError as error:
        assert "拒绝返回/固化" in str(error)
    else:
        raise AssertionError("empty MockAgent result must fail closed")


def test_deerflow_runtime_mock_pool_uses_dynamic_generator(monkeypatch):
    generated = [{"id": "dynamic"}]
    monkeypatch.setattr(
        pipeline,
        "generate_mock_cases",
        lambda project_id, count=3, cases_per_scenario=0: generated,
    )
    monkeypatch.setattr(
        pipeline,
        "_fixture_mock_cases",
        lambda _project_id: (_ for _ in ()).throw(
            AssertionError("deerflow runtime must not read fixture first")
        ),
    )

    assert pipeline.mock_cases("deerflow", count=3) is generated


def test_deerflow_source_generation_resolves_scenario_goal(monkeypatch):
    captured = {}

    class _ProjectMock:
        def generate_mock_case(self, **kwargs):
            captured.update(kwargs)
            return SingleTurnCase(
                id="generated-planning",
                input={
                    "input": {"messages": [{"role": "user", "content": "下个月 NBEV 目标定 800 万，帮我推演一下。"}]},
                    "config": {"configurable": {}},
                },
                scenario=kwargs["scenario"],
                user_intent=kwargs["intent"],
                metadata={
                    "mock_intent": {
                        "user_intent": kwargs["intent"],
                        "query": "下个月 NBEV 目标定 800 万，帮我推演一下。",
                        "user_context": {},
                        "scenario": kwargs["scenario"],
                    }
                },
            )

    monkeypatch.setattr(pipeline, "load_project_role_instance", lambda *_args: _ProjectMock())
    monkeypatch.setattr(pipeline.random, "choice", lambda choices: choices[-1])
    case = to_dict(pipeline.mock_build_intent("deerflow", scenario="single_turn_planning"))

    expected = MOCK_CASE_SEEDS["single_turn_planning"]["requested_intents"][-1]
    assert captured["intent"] == expected
    assert case["intent"]["user_intent"] == expected
    assert case["live_request"]["config"]["configurable"] == {}


def test_frontend_dynamic_generation_uses_enabled_deerflow_mock_draft(monkeypatch):
    calls = []

    class _Llm:
        def complete_json(self, system, user, **_kwargs):
            calls.append((system, json.loads(user)))
            return {
                "query": "刚才保存后一直转圈，这是提交成功了吗？",
                "user_intent": "确认刚才的方案调整是否保存成功",
            }

    production_spec = load_project("deerflow")
    draft_spec = _with_mock_draft(production_spec)
    monkeypatch.setattr(pipeline, "load_project", lambda _project_id: draft_spec)
    monkeypatch.setattr(llm_client, "project_llm_client", lambda *_args, **_kwargs: _Llm())

    case = to_dict(pipeline.mock_build_intent("deerflow", scenario="open_world_user"))

    assert len(calls) == 1
    assert calls[0][1]["template"]["generation_mode"] == "open_world_user_population"
    assert case["intent"]["query"] == "刚才保存后一直转圈，这是提交成功了吗？"
    assert case["intent"]["user_intent"] == "确认刚才的方案调整是否保存成功"
    assert case["live_request"] == {
        "input": {
            "messages": [
                {"role": "user", "content": "刚才保存后一直转圈，这是提交成功了吗？"}
            ]
        },
        "config": {"configurable": {}},
    }


def test_interactive_scenario_configuration_errors_are_not_silently_downgraded(monkeypatch):
    from impl.core import project_loader

    monkeypatch.setattr(
        project_loader,
        "load_project",
        lambda _project_id: (_ for _ in ()).throw(RuntimeError("broken project config")),
    )

    with pytest.raises(RuntimeError, match="broken project config"):
        normalize_case_interaction(
            "deerflow",
            SingleTurnCase(
                id="multi",
                scenario="multi_turn_dimension_accumulation",
                user_intent="规划 NBEV",
                input={"input": {"messages": []}, "config": {"configurable": {}}},
            ),
        )


def test_deerflow_next_turn_accepts_trace_and_runtime_output_field_names(monkeypatch):
    captured = []

    class _MockAgent:
        def __init__(self, _spec):
            pass

        def next_turn(self, case, previous_turns, live_feedback):
            captured.append((case, previous_turns, live_feedback))
            return {"query": "继续从客户视角看目标达成情况"}

    monkeypatch.setattr("impl.core.mock_agent.MockAgent", _MockAgent)
    implementation = load_project_role_instance(
        load_project("deerflow"),
        "mock",
        load_adapter(load_project("deerflow")),
    )
    intent = type(
        "Intent",
        (),
        {
            "scenario": "multi_turn_dimension_accumulation",
            "user_context": {},
            "user_intent": "规划下月 NBEV 达成路径",
        },
    )()

    implementation.build_next_request(
        intent,
        {
            "turns": [
                {
                    "extracted_output": {
                        "stage": "planning",
                        "missing_fields": ["客户视角"],
                        "session_summary": {"thread_id": "trace-thread"},
                    }
                }
            ]
        },
    )
    assert captured[-1][2]["stage"] == "planning"
    assert captured[-1][2]["missing_fields"] == ["客户视角"]

    request = implementation.build_next_request(
        intent,
        {
            "turns": [
                {
                    "extract_output": {
                        "stage": "clarification",
                        "missing_fields": ["月份"],
                        "session_summary": {"thread_id": "runtime-thread"},
                    }
                }
            ]
        },
    )
    assert captured[-1][2]["stage"] == "clarification"
    assert request["config"]["configurable"]["thread_id"] == "runtime-thread"


def test_deerflow_draft_adds_semantic_user_language_policy(monkeypatch):
    captured = {}

    class _Llm:
        def complete_json(self, system, user, **_kwargs):
            captured["system"] = system
            captured["user"] = json.loads(user)
            return {"query": "接着看看客户视角能贡献多少 NBEV"}

    monkeypatch.setattr(llm_client, "project_llm_client", lambda *_args, **_kwargs: _Llm())
    spec = _mock_variant(False)
    draft_spec = _with_mock_draft(spec)
    implementation = load_project_role_instance(
        draft_spec,
        "mock",
        load_adapter(draft_spec),
    )
    intent = type(
        "Intent",
        (),
        {
            "scenario": "multi_turn_dimension_accumulation",
            "user_context": {"goal": "下月 900 万 NBEV"},
            "user_intent": "逐步查看产品、队伍和客户视角的目标达成情况",
        },
    )()

    implementation.build_next_request(intent, {"turns": []})

    assert "用户目标" in captured["system"]
    assert "可见业务结果" in captured["system"]
    assert "内部技能" not in captured["system"]
    assert "固定句式" not in captured["system"]
    assert "next_turn_policy" not in captured["user"]

    production = load_project_role_instance(
        spec,
        "mock",
        load_adapter(spec),
    )
    production.build_next_request(intent, {"turns": []})
    assert "用户目标" not in captured["system"]


def test_draft_repairs_internal_identifier_only_when_model_emits_one(monkeypatch):
    calls = []

    class _Llm:
        def complete_json(self, system, user, **_kwargs):
            calls.append(system)
            if "只改写下面这句" in system:
                return {"query": "那继续看看客户视角的 NBEV 达成情况"}
            return {"query": "请用 nbev_planning_v2 帮我继续规划"}

    monkeypatch.setattr(llm_client, "project_llm_client", lambda *_args, **_kwargs: _Llm())
    spec = load_project("deerflow")
    draft_spec = _with_mock_draft(spec)
    implementation = load_project_role_instance(draft_spec, "mock", load_adapter(draft_spec))
    intent = type(
        "Intent",
        (),
        {"scenario": "multi_turn_dimension_accumulation", "user_context": {}, "user_intent": "继续规划 NBEV"},
    )()

    request = implementation.build_next_request(intent, {"turns": []})

    assert request["input"]["messages"][-1]["content"] == "那继续看看客户视角的 NBEV 达成情况"
    assert len(calls) == 2


def test_nbev_planning_shortfall_is_not_non_agent():
    reply = """## 8 月 NBEV 达成分析
- 产品视角预计贡献 520 万
- 队伍视角预计贡献 380 万
- 客户视角按当前条件无法单独达到 900 万目标，需要组合推进
"""

    assert _stage_inference(reply, [], []) == (
        "planning",
        "structured_planning_reply",
    )
    assert _stage_inference("抱歉，无法帮你查询天气。", [], []) == (
        "non_agent",
        "non_agent_reply",
    )
    assert _stage_inference(
        "## NBEV 产品规划还需确认\n- 请补充目标月份\n- 请提供目标 NBEV",
        [],
        [],
    ) == ("clarification", "explicit_missing_information_request")


def test_optional_intent_reuses_initial_visible_message_without_top_level_query():
    spec = load_project("deerflow")
    adapter = load_adapter(spec)
    live = adapter.live()
    mock = adapter.mock()
    case = SingleTurnCase(
        id="intent-without-query",
        scenario="multi_turn_dimension_accumulation",
        user_intent="围绕下月 900 万 NBEV 目标逐步分析产品、队伍和客户",
        input={
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": "先看看产品这边的情况，后面再结合队伍和客户。",
                    }
                ]
            },
            "config": {"configurable": {}},
        },
    )

    resolved = live._resolve_intent(case, mock)

    assert resolved is not None
    assert resolved.user_intent == case.user_intent
    assert resolved.query == "先看看产品这边的情况，后面再结合队伍和客户。"
