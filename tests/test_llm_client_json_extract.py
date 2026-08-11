from __future__ import annotations

from dataclasses import dataclass, replace

from impl.core.config import get_llm_config
from impl.core.llm_client import (
    LlmClient,
    _select_schema_matching_object,
    _supported_agent_kwargs,
    _tool_budget_error,
    extract_json,
)
from impl.core.judge import _build_judge_output_spec
from impl.core.schema.judge import JudgeLLMOutput
from impl.core.structured_output import StructuredOutputSpec, enforce_output, render_output_constraint


def test_extract_json_parses_plain_and_fenced_json():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_supported_agent_kwargs_omit_options_missing_from_installed_agent():
    class LegacyAgent:
        def __init__(self, *, model=None, tools=None):
            self.model = model
            self.tools = tools

    assert _supported_agent_kwargs(
        LegacyAgent,
        {
            "model": "model",
            "tools": ["tool"],
            "compress_tool_results": True,
            "max_tool_calls_from_history": 3,
        },
    ) == {
        "model": "model",
        "tools": ["tool"],
    }


def test_supported_agent_kwargs_preserve_options_for_flexible_factory():
    def flexible_factory(**kwargs):
        return kwargs

    kwargs = {"model": "model", "compress_tool_results": True}
    assert _supported_agent_kwargs(flexible_factory, kwargs) == kwargs


def test_tool_budget_is_checked_against_actual_calls_not_sdk_rounds():
    calls = [{"tool_name": "search_context_units"}] * 7

    assert _tool_budget_error(calls[:6], 6) is None
    assert _tool_budget_error(calls, 6) == (
        "actual tool calls 7 exceed configured limit 6"
    )


def test_extract_json_repairs_unescaped_quotes_inside_string_values():
    bad = '```json\n{"description": "用户口语"重疾险"应映射"}\n```'

    assert extract_json(bad) == {"description": "用户口语\"重疾险\"应映射"}


def test_repaired_judge_output_still_passes_the_strict_judge_schema():
    raw = (
        '{"business_expectations":[{"expectation_id":"儿子关系",'
        '"blocking":true,"user_intent":"用户查询"儿子生日""}],'
        '"fulfillment_assessments":[{"expectation_id":"儿子关系",'
        '"status":"fulfilled"}],"reasoning_summary":"条件满足"}'
    )
    spec = _build_judge_output_spec(
        has_actual=True,
        project_id="client_search",
        has_reference=True,
    )

    repaired = extract_json(raw)
    enforce_output(repaired, spec, caller="judge")

    assert repaired["business_expectations"][0]["user_intent"] == '用户查询"儿子生日"'


def test_render_output_constraint_requires_json_only_output():
    spec = StructuredOutputSpec.from_dataclass(
        JudgeLLMOutput,
        required_nonempty=["business_expectations", "overall_fulfillment", "reasoning_summary"],
    )

    prompt = render_output_constraint(spec)

    assert "不要使用 ```json 代码块" in prompt
    assert "首字符必须是 `{`" in prompt
    assert "末字符必须是 `}`" in prompt
    assert "未转义英文双引号" in prompt


@dataclass
class _InvestigationOutput:
    investigation_summary: str


def test_complete_json_classifies_agno_error_before_json_parsing(monkeypatch):
    class Result:
        content = ""
        status = type("Status", (), {"value": "ERROR"})()
        metrics = None

        def to_dict(self):
            return {"content": "", "status": "ERROR", "model_provider": "DeepSeek"}

    class FakeAgent:
        def __init__(self, **_kwargs):
            pass

        def run(self, _user):
            return Result()

    monkeypatch.setattr("impl.core.llm_client.Agent", FakeAgent)
    monkeypatch.setattr("impl.core.llm_client.OpenAILike", lambda **_kwargs: object())
    monkeypatch.setattr("impl.core.llm_client._track_context", lambda *_args, **_kwargs: None)

    client = LlmClient(config=replace(get_llm_config(), api_key="test-key"))
    result = client.complete_json(
        "system",
        "user",
        output_spec=StructuredOutputSpec.from_dataclass(_InvestigationOutput),
    )

    assert result["error"] == "llm_request_failed"
    assert "status ERROR" in result["raw_text"]
    assert result["raw_model_response"]["status"] == "ERROR"


def test_complete_json_records_stage_and_each_application_attempt(monkeypatch):
    calls = {"count": 0}
    tracked = []

    class Result:
        content = '{"investigation_summary":"ok"}'
        status = type("Status", (), {"value": "COMPLETED"})()
        metrics = None
        messages = []

        def to_dict(self):
            return {"content": self.content, "status": "COMPLETED"}

    class FakeAgent:
        def __init__(self, **_kwargs):
            pass

        def run(self, _user):
            calls["count"] += 1
            if calls["count"] == 1:
                raise TimeoutError("provider timeout")
            return Result()

    monkeypatch.setattr("impl.core.llm_client.Agent", FakeAgent)
    monkeypatch.setattr("impl.core.llm_client.OpenAILike", lambda **_kwargs: object())
    monkeypatch.setattr(
        "impl.core.llm_client._track_context",
        lambda *_args, **kwargs: tracked.append(kwargs.get("runtime")),
    )
    monkeypatch.setattr("impl.core.llm_client.time.sleep", lambda _seconds: None)

    client = LlmClient(config=replace(get_llm_config(), api_key="test-key"))
    result = client.complete_json(
        "system",
        "user",
        stage="judge-plan-semantic-review",
        output_spec=StructuredOutputSpec.from_dataclass(_InvestigationOutput),
    )

    assert result["investigation_summary"] == "ok"
    assert tracked[-1]["stage"] == "judge-plan-semantic-review"
    assert [item["status"] for item in tracked[-1]["attempts"]] == [
        "failed",
        "succeeded",
    ]
    assert tracked[-1]["attempts"][0]["error_type"] == "TimeoutError"
    attempts = tracked[-1]["attempts"]
    assert len({item["endpoint"] for item in attempts}) == 2
    assert all(item["model"] for item in attempts)
    assert tracked[-1]["selected_endpoint"] == attempts[-1]["endpoint"]
    assert tracked[-1]["selected_model"] == attempts[-1]["model"]
    assert all(item["elapsed_ms"] >= 0 for item in tracked[-1]["attempts"])


def test_schema_matching_object_ignores_leading_tool_span_and_repaired_list():
    text = (
        '匹配位置 [10, 14]，结论如下：\n'
        '{"investigation_summary":"当前输入命中 homepage rule。"}'
    )
    repaired = extract_json(text)

    selected = _select_schema_matching_object(
        text,
        repaired,
        StructuredOutputSpec.from_dataclass(_InvestigationOutput),
    )

    assert selected == {"investigation_summary": "当前输入命中 homepage rule。"}


def test_schema_matching_object_can_recover_from_top_level_list_without_repairing_fields():
    text = '[[10, 14], {"investigation_summary":"当前输入命中 homepage rule。"}]'

    selected = _select_schema_matching_object(
        text,
        extract_json(text),
        StructuredOutputSpec.from_dataclass(_InvestigationOutput),
    )

    assert selected == {"investigation_summary": "当前输入命中 homepage rule。"}


def test_schema_matching_object_does_not_accept_wrong_embedded_shape():
    selected = _select_schema_matching_object(
        '说明 {"summary":"字段名错误"}',
        {"summary": "字段名错误"},
        StructuredOutputSpec.from_dataclass(_InvestigationOutput),
    )

    assert selected == {"summary": "字段名错误"}


def test_complete_json_falls_back_to_second_endpoint_within_one_call(monkeypatch):
    calls = {"count": 0}
    route = []

    class Result:
        content = '{"investigation_summary":"ok"}'
        status = type("Status", (), {"value": "COMPLETED"})()
        metrics = None
        messages = []

        def to_dict(self):
            return {"content": self.content, "status": "COMPLETED"}

    class FakeOpenAILike:
        def __init__(self, **kwargs):
            self.base_url = kwargs.get("base_url")
            self.model = kwargs.get("id")

    class FakeAgent:
        def __init__(self, **kwargs):
            self.model = kwargs["model"]

        def run(self, _user):
            calls["count"] += 1
            base = str(getattr(self.model, "base_url", ""))
            route.append(base)
            if "127.0.0.1:9" in base:
                raise ConnectionError("connection refused (simulated dead endpoint)")
            return Result()

    monkeypatch.setattr("impl.core.llm_client.Agent", FakeAgent)
    monkeypatch.setattr("impl.core.llm_client.OpenAILike", FakeOpenAILike)
    monkeypatch.setattr("impl.core.llm_client._track_context", lambda *_a, **_k: None)
    monkeypatch.setattr("impl.core.llm_client.time.sleep", lambda _s: None)

    from impl.core.llm_router import LlmEndpoint, LlmRouter

    client = LlmClient(config=replace(get_llm_config(), api_key="test-key"))
    client.llm_router = LlmRouter(
        [
            LlmEndpoint(name="primary", base_url="http://127.0.0.1:9/v1", model="m", api_key="k"),
            LlmEndpoint(name="fallback1", base_url="http://fallback.example/v1", model="m", api_key="k"),
        ]
    )

    result = client.complete_json(
        "system",
        "user",
        stage="judge-plan-semantic-review",
        output_spec=StructuredOutputSpec.from_dataclass(_InvestigationOutput),
    )

    assert result["investigation_summary"] == "ok"
    assert calls["count"] == 2
    assert "127.0.0.1:9" in route[0]
    assert "fallback.example" in route[1]
