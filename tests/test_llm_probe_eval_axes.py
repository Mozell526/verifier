"""llm_probe 扩展评估轴（试验体系）：一个 trace → 两个 AxisResult，依赖 / 筛选 / 隔离 / 校验。

LLM 用确定性假客户端：monkeypatch impl.core.llm_client.project_llm_client，
按 role 分发——judge 给轴1，capability_carrier_mapper 给轴2。
"""
from __future__ import annotations

import json
from typing import Any, Callable

import pytest

from impl.core.capability_carrier import PLACEMENT_CANNOT, PLACEMENT_WRONG
from impl.core.capability_store import validate_entry
from impl.core.project_loader import load_project
from impl.core.schema import RunTrace
from impl.projects.llm_probe.eval_axes import runner as runner_module
from impl.projects.llm_probe.eval_axes.registry import AXIS_TYPES, describe_axis_types, get_axis_type
from impl.projects.llm_probe.eval_axes.runner import run_axes, topo_order
from impl.projects.llm_probe.eval_axes.types import (
    STATUS_BLOCKED,
    STATUS_DISABLED,
    STATUS_FAILED,
    STATUS_NOT_APPLICABLE,
    STATUS_SUCCEEDED,
    AxisType,
    ExecutionLimits,
    Field,
    Input,
    RunOutcome,
    ScenarioAxis,
    Verdict,
    When,
)
from impl.projects.llm_probe.eval_axes.validate import parse_axes, validate_scenario_axes

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

CAPABILITY = "用户拿它办的事：从客户库检回符合描述的客户。交付物是查询条件。"
BOUNDARY = "本接口仅支持按客户姓名检索，不支持年龄。"
EXPECTATION = "按年龄筛选客户"


FAKE_MODEL = "fake-judge-model"


def _fake_router(*endpoints):
    from impl.core.llm_router import LlmEndpoint, LlmRouter

    endpoints = endpoints or (("primary", FAKE_MODEL),)
    return LlmRouter([LlmEndpoint(name=name, base_url="http://fake", model=model, api_key="x") for name, model in endpoints])


class FakeLlm:
    """模拟 LlmClient 与路由交互的最小面：select → 调用 → record_success；select 抛错则像真客户端一样返回 error 字典。"""

    def __init__(self, role: str, script: Callable[[str, str, str], dict], router=None) -> None:
        self.role = role
        self.model = FAKE_MODEL
        self.llm_router = router or _fake_router()
        self._script = script
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, system: str, user: str, trace_id: str | None = None, output_spec: Any = None, **kwargs: Any) -> dict:
        self.calls.append({"system": system, "user": user, "trace_id": trace_id, **kwargs})
        try:
            endpoint = self.llm_router.select()
        except RuntimeError as exc:
            return {"error": "llm_request_failed", "raw_text": str(exc)}
        self.llm_router.record_success(endpoint)
        return self._script(self.role, system, user)


def _judge_payload(status: str) -> dict:
    return {
        "business_expectations": [{
            "expectation_id": EXPECTATION,
            "blocking": True,
            "user_intent": "找 30 岁以下客户",
            "expected_outcome": "输出带年龄条件",
            "acceptance_criteria": ["条件里有 age<30"],
        }],
        "fulfillment_assessments": [{
            "expectation_id": EXPECTATION,
            "status": status,
            "expected_evidence": ["age<30"],
            "actual_evidence": ["无年龄条件"],
        }],
        "expected": {"output_text": "{\"conditions\": [{\"field\": \"age\"}]}"},
        "reasoning_summary": "输出缺少年龄条件",
    }


def _carrier_payload(carry: str) -> dict:
    if carry == "no":
        return {
            "carry": "no",
            "reason": "边界写明不支持年龄",
            "self_recognition": "不支持年龄",
            "citations": [{"source": "boundary", "ref": "boundary", "note": "不支持年龄"}],
        }
    return {
        "carry": "yes",
        "reason": "边界覆盖姓名检索",
        "citations": [{"source": "boundary", "ref": "boundary", "note": "支持按客户姓名检索"}],
    }


def _install_fake_llm(monkeypatch, *, judge_status: str = "not_fulfilled", carry: str = "no", judge_error: bool = False, router_factory=None) -> list[FakeLlm]:
    created: list[FakeLlm] = []

    def script(role: str, _system: str, _user: str) -> dict:
        if role == "judge":
            if judge_error:
                return {"error": "llm down"}
            return _judge_payload(judge_status)
        if role == "capability_carrier_mapper":
            return _carrier_payload(carry)
        raise AssertionError(f"unexpected role {role}")

    def factory(_spec: Any, role: str, **_kwargs: Any) -> FakeLlm:
        client = FakeLlm(role, script, router=router_factory() if router_factory else None)
        created.append(client)
        return client

    monkeypatch.setattr("impl.core.llm_client.project_llm_client", factory)
    return created


def _trace(output_text: str = '{"conditions": []}') -> RunTrace:
    return RunTrace(
        trace_id="probe-trace-1",
        project_id="llm_probe",
        case_id="case-1",
        normalized_request={
            "body": {"user_text": "找 30 岁以下客户"},
            "url": "http://127.0.0.1:9/llm-probe",
            "capability_ref": "client_search",
        },
        extracted_output={"output_text": output_text},
    )


def _axes(*, fulfillment_enabled: bool = True, carryability_enabled: bool = True) -> list[ScenarioAxis]:
    return [
        ScenarioAxis("fulfillment", fulfillment_enabled, CAPABILITY),
        ScenarioAxis("carryability", carryability_enabled, BOUNDARY),
    ]


def _by_id(results) -> dict[str, Any]:
    return {item.axis_id: item for item in results}


# ---------------------------------------------------------------- 类型可见


def test_registry_exposes_two_types_with_frozen_enums() -> None:
    described = {item["type_id"]: item for item in describe_axis_types()}
    assert set(described) == {"fulfillment", "carryability"}
    assert [v["value"] for v in described["fulfillment"]["verdict_enum"]] == ["fulfilled", "not_fulfilled", "not_evaluable"]
    assert [v["value"] for v in described["carryability"]["verdict_enum"]] == ["做不了", "做错了", "说不清"]
    assert described["fulfillment"]["verdict_scope"] == "axis"
    assert described["carryability"]["verdict_scope"] == "item"
    assert described["carryability"]["depend_on"] == ["fulfillment"]
    assert described["carryability"]["trigger_when"] == {"axis": "fulfillment", "verdict_in": ["not_fulfilled"]}
    # 轴2没有任何 sample 来源：不看这次交付了什么
    assert all(item["source"].startswith("axis.") for item in described["carryability"]["inputs"])


# ---------------------------------------------------------------- 复制等价：prompt 材料必须与生产轴1逐字相同


def test_fulfillment_context_is_byte_identical_to_production_build_context() -> None:
    """新轴1的 build_context 是旧轴1的复制：同一 trace、同一能力文本，system/user 材料逐字相同。

    真实模型对照时曾发现 system_extras 少一处字符串拼接导致多一个空行；这条测试把它钉死。
    """
    from impl.projects.llm_probe.eval_axes.adapters.fulfillment import build_context
    from impl.projects.llm_probe.judge import LlmProbeJudge

    spec = load_project("llm_probe")
    for output_text in ('{"conditions": [{"field": "age", "operator": "GT", "value": 30}]}', "plain text answer", ""):
        trace = RunTrace(
            trace_id="probe-trace-1",
            project_id="llm_probe",
            case_id="case-1",
            normalized_request={
                "body": {"user_text": "找 30 岁以下客户"},
                "url": "http://127.0.0.1:9/llm-probe",
                "method": "POST",
                "headers": {"Authorization": "Bearer secret", "X-Trace": "1"},
                "capability": CAPABILITY,           # 生产路径直接用请求内联的能力文本
                "show_schema": {"fields": ["conditions"]},
            },
            extracted_output={"output_text": output_text},
        )
        production = LlmProbeJudge(spec).build_context(trace)
        production["intent_frame"] = LlmProbeJudge(spec).build_intent_frame(trace, production)
        ours = build_context(spec, trace, CAPABILITY)
        assert ours["system_prompt_extras"] == production["system_prompt_extras"]
        assert ours["user_prompt_extras"] == production["user_prompt_extras"]
        assert ours["user_intent"] == production["user_intent"]
        assert ours["intent_frame"] == production["intent_frame"]


# ---------------------------------------------------------------- 端到端


def test_one_trace_yields_two_results_with_isolation(monkeypatch) -> None:
    clients = _install_fake_llm(monkeypatch, judge_status="not_fulfilled", carry="no")
    spec = load_project("llm_probe")
    results = _by_id(run_axes(spec, _trace(), _axes(), scenario_id="client_search", run_id="axes-test"))

    fulfillment = results["fulfillment"]
    assert fulfillment.status == STATUS_SUCCEEDED
    assert fulfillment.title == "能力兑现"
    assert fulfillment.verdict == "not_fulfilled"
    assert fulfillment.verdict_description
    # summary 复制旧轴1：一句话 = summary_from_fulfillment 的 reason，逐格 = 每条期望的 status + 证据
    assert fulfillment.summary["text"] == fulfillment.output["summary"]["reason"]
    assert fulfillment.summary["text"].startswith("not_fulfilled · blocking=[" + EXPECTATION + "]")
    assert fulfillment.summary["items"] == [{
        "key": EXPECTATION, "value": "not_fulfilled", "reason": "无年龄条件 | age<30", "blocking": True,
    }]
    assert set(fulfillment.output) == set(AXIS_TYPES["fulfillment"].output_fields)
    assert fulfillment.output["overall_fulfillment"]["status"] == "not_fulfilled"
    assert fulfillment.inputs_used == {"trace": "sample.trace@probe-trace-1"}
    assert fulfillment.usage["llm_calls"] == 1
    # 实际命中的模型/端点进 usage（axe-v4 D12）
    assert fulfillment.usage["llm_model"] == FAKE_MODEL
    assert fulfillment.usage["llm_endpoint"] == "primary"
    assert fulfillment.usage["model_policy"] == "any"
    assert fulfillment.execution_trace_ref == "axes-test:probe-trace-1"

    carryability = results["carryability"]
    assert carryability.status == STATUS_SUCCEEDED
    assert carryability.verdict is None  # item 级没有轴级单值
    assert carryability.trigger_decision["trigger_when_matched"]["matched"] is True
    assert list(carryability.inputs_used) == ["fulfillment"]
    assert "sample" not in json.dumps(carryability.inputs_used)
    placements = carryability.output["placements"]
    assert [item["placement"] for item in placements] == [PLACEMENT_CANNOT]
    assert placements[0]["expectation_id"] == EXPECTATION
    assert placements[0]["recognition"] == "boundary_statement"
    assert carryability.output["errors"] == []
    assert carryability.usage["llm_calls"] == 1
    assert carryability.usage["llm_model"] == FAKE_MODEL
    assert carryability.usage["tool_calls"] == 0
    # summary 复制旧轴2：一句话 = "裁决"列原文 carrier_text，逐格 = 每条归位 + 理由
    from impl.core.capability_carrier import carrier_text
    assert carryability.summary["text"] == carrier_text(carryability.output)
    assert carryability.summary["text"].startswith("$做不了\n")
    assert carryability.summary["items"] == [{
        "key": EXPECTATION, "value": PLACEMENT_CANNOT, "reason": "边界写明不支持年龄", "carry": "no",
    }]

    judge_calls = [c for client in clients if client.role == "judge" for c in client.calls]
    carrier_calls = [c for client in clients if client.role == "capability_carrier_mapper" for c in client.calls]
    assert len(judge_calls) == 1 and len(carrier_calls) == 1
    # 特化可见：框里的描述进了轴1 prompt
    assert CAPABILITY in judge_calls[0]["user"]
    # 信息隔离：轴2 prompt 只有期望 + 边界，没有这次的回答
    assert BOUNDARY in carrier_calls[0]["user"]
    assert EXPECTATION in carrier_calls[0]["user"]
    assert '{"conditions": []}' not in carrier_calls[0]["user"]
    assert "conditions" not in carrier_calls[0]["user"]
    # 试验的 LLM 调用统一挂在 axes- 前缀的 trace_id 下
    assert judge_calls[0]["trace_id"] == "axes-test:probe-trace-1"
    assert carrier_calls[0]["trace_id"] == "axes-test:probe-trace-1"


def test_carry_yes_places_wrong(monkeypatch) -> None:
    _install_fake_llm(monkeypatch, judge_status="not_fulfilled", carry="yes")
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(), scenario_id="client_search"))
    assert results["carryability"].status == STATUS_SUCCEEDED
    assert [p["placement"] for p in results["carryability"].output["placements"]] == [PLACEMENT_WRONG]


def test_fulfilled_makes_carryability_not_applicable_without_llm_call(monkeypatch) -> None:
    clients = _install_fake_llm(monkeypatch, judge_status="fulfilled")
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(), scenario_id="client_search"))
    assert results["fulfillment"].verdict == "fulfilled"
    carryability = results["carryability"]
    assert carryability.status == STATUS_NOT_APPLICABLE
    assert carryability.output is None
    assert carryability.trigger_decision["depend_on_satisfied"] is True
    assert carryability.trigger_decision["trigger_when_matched"]["verdict"] == "fulfilled"
    assert carryability.summary == {"text": "fulfillment=fulfilled，不在筛选范围 [not_fulfilled]，不判", "items": []}
    assert not [c for c in clients if c.role == "capability_carrier_mapper"]


def test_not_evaluable_also_skips_carryability(monkeypatch) -> None:
    _install_fake_llm(monkeypatch, judge_status="not_evaluable")
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(), scenario_id="client_search"))
    assert results["fulfillment"].status == STATUS_SUCCEEDED
    assert results["fulfillment"].verdict == "not_evaluable"
    assert results["carryability"].status == STATUS_NOT_APPLICABLE


def test_judge_failure_is_failed_status_and_blocks_downstream(monkeypatch) -> None:
    clients = _install_fake_llm(monkeypatch, judge_error=True)
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(), scenario_id="client_search"))
    fulfillment = results["fulfillment"]
    assert fulfillment.status == STATUS_FAILED
    assert fulfillment.verdict is None          # 没跑成进 status，不伪装成 not_evaluable
    assert "llm_call_failed" in fulfillment.error
    assert fulfillment.output is not None        # 诊断保留
    assert fulfillment.summary["text"] == fulfillment.error
    carryability = results["carryability"]
    assert carryability.status == STATUS_BLOCKED
    assert carryability.trigger_decision == {"depend_on_satisfied": False, "upstream": {"fulfillment": STATUS_FAILED}}
    assert carryability.summary == {"text": "上游未成功：fulfillment=failed", "items": []}
    assert not [c for c in clients if c.role == "capability_carrier_mapper"]


def test_disabled_axis_is_recorded_not_run(monkeypatch) -> None:
    clients = _install_fake_llm(monkeypatch)
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(carryability_enabled=False), scenario_id="client_search"))
    assert results["carryability"].status == STATUS_DISABLED
    assert not [c for c in clients if c.role == "capability_carrier_mapper"]


def test_topo_order_puts_upstream_first(monkeypatch) -> None:
    _install_fake_llm(monkeypatch)
    reversed_axes = list(reversed(_axes()))
    assert [a.type_id for a in topo_order(reversed_axes)] == ["fulfillment", "carryability"]
    results = run_axes(load_project("llm_probe"), _trace(), reversed_axes, scenario_id="client_search")
    assert [r.axis_id for r in results] == ["fulfillment", "carryability"]
    assert results[1].status == STATUS_SUCCEEDED


def test_fingerprints_are_stable_and_config_sensitive(monkeypatch) -> None:
    _install_fake_llm(monkeypatch)
    spec = load_project("llm_probe")
    first = _by_id(run_axes(spec, _trace(), _axes(), scenario_id="client_search"))
    second = _by_id(run_axes(spec, _trace(), _axes(), scenario_id="client_search"))
    assert first["fulfillment"].config_fingerprint == second["fulfillment"].config_fingerprint
    assert first["fulfillment"].implementation_fingerprint == second["fulfillment"].implementation_fingerprint
    changed = _by_id(run_axes(spec, _trace(), [ScenarioAxis("fulfillment", True, CAPABILITY + "。多一句"), _axes()[1]], scenario_id="client_search"))
    assert changed["fulfillment"].config_fingerprint != first["fulfillment"].config_fingerprint


# ---------------------------------------------------------------- 运行器对 adapter 输出的校验


def test_runner_rejects_output_not_matching_declared_fields(monkeypatch) -> None:
    def bad_run(_inputs, _axis, _runtime) -> RunOutcome:
        return RunOutcome(output={"verdict": "ok", "extra": 1})

    custom = AxisType(
        type_id="custom",
        title="c",
        summary="c",
        verdict_scope="axis",
        verdict_enum=(Verdict("ok", "ok"),),
        depend_on=(),
        trigger_when=None,
        inputs=(Input("trace", source="sample.trace"),),
        output_fields=("verdict",),
        verdict_path="verdict",
        scenario_fields=(Field("description"),),
        limits=ExecutionLimits(),
        run=bad_run,
    )
    monkeypatch.setattr(runner_module, "get_axis_type", lambda type_id: custom if type_id == "custom" else get_axis_type(type_id))
    results = run_axes(load_project("llm_probe"), _trace(), [ScenarioAxis("custom", True, "x")], scenario_id="client_search")
    assert results[0].status == STATUS_FAILED
    assert "output 键集" in results[0].error


def test_runner_rejects_verdict_outside_enum(monkeypatch) -> None:
    custom = AxisType(
        type_id="custom",
        title="c",
        summary="c",
        verdict_scope="axis",
        verdict_enum=(Verdict("ok", "ok"),),
        depend_on=(),
        trigger_when=None,
        inputs=(Input("trace", source="sample.trace"),),
        output_fields=("verdict",),
        verdict_path="verdict",
        scenario_fields=(Field("description"),),
        limits=ExecutionLimits(),
        run=lambda _i, _a, _r: RunOutcome(output={"verdict": "maybe"}),
    )
    monkeypatch.setattr(runner_module, "get_axis_type", lambda type_id: custom if type_id == "custom" else get_axis_type(type_id))
    results = run_axes(load_project("llm_probe"), _trace(), [ScenarioAxis("custom", True, "x")], scenario_id="client_search")
    assert results[0].status == STATUS_FAILED
    assert "不在枚举" in results[0].error


def test_adapter_exception_is_isolated_to_that_axis(monkeypatch) -> None:
    def boom(_inputs, _axis, _runtime) -> RunOutcome:
        raise RuntimeError("adapter exploded")

    custom = AxisType(
        type_id="custom",
        title="c",
        summary="c",
        verdict_scope="axis",
        verdict_enum=(Verdict("ok", "ok"),),
        depend_on=(),
        trigger_when=None,
        inputs=(Input("trace", source="sample.trace"),),
        output_fields=("verdict",),
        verdict_path="verdict",
        scenario_fields=(Field("description"),),
        limits=ExecutionLimits(),
        run=boom,
    )
    _install_fake_llm(monkeypatch, judge_status="fulfilled")
    monkeypatch.setattr(runner_module, "get_axis_type", lambda type_id: custom if type_id == "custom" else get_axis_type(type_id))
    results = _by_id(run_axes(
        load_project("llm_probe"),
        _trace(),
        [ScenarioAxis("custom", True, "x"), ScenarioAxis("fulfillment", True, CAPABILITY)],
        scenario_id="client_search",
    ))
    assert results["custom"].status == STATUS_FAILED
    assert "adapter exploded" in results["custom"].error
    assert results["fulfillment"].status == STATUS_SUCCEEDED


def test_runner_requires_summary_for_succeeded_axis(monkeypatch) -> None:
    custom = AxisType(
        type_id="custom",
        title="c",
        summary="c",
        verdict_scope="axis",
        verdict_enum=(Verdict("ok", "ok"),),
        depend_on=(),
        trigger_when=None,
        inputs=(Input("trace", source="sample.trace"),),
        output_fields=("verdict",),
        verdict_path="verdict",
        scenario_fields=(Field("description"),),
        limits=ExecutionLimits(),
        run=lambda _i, _a, _r: RunOutcome(output={"verdict": "ok"}),   # 只交枚举，不交解释
    )
    monkeypatch.setattr(runner_module, "get_axis_type", lambda type_id: custom if type_id == "custom" else get_axis_type(type_id))
    results = run_axes(load_project("llm_probe"), _trace(), [ScenarioAxis("custom", True, "x")], scenario_id="client_search")
    assert results[0].status == STATUS_FAILED
    assert "summary" in results[0].error
    assert results[0].summary["text"] == results[0].error


# ---------------------------------------------------------------- 模型策略（axe-v4 D12）：any 按路由回退；same_model 只允许同名模型端点


def _cool_down(router, endpoint_name: str) -> None:
    endpoint = next(ep for ep in router.endpoints if ep.name == endpoint_name)
    for _ in range(router.failure_threshold):
        router.record_failure(endpoint)


def test_router_view_any_falls_back_across_models_and_records_selection() -> None:
    from impl.projects.llm_probe.eval_axes.llm import AxisLlm

    router = _fake_router(("primary", "gpt-x"), ("fallback1", "gpt-x"), ("fallback2", "deepseek-y"))
    client = FakeLlm("judge", lambda *_: {"ok": True}, router=router)
    shell = AxisLlm(client, policy="any")
    _cool_down(router, "primary")
    _cool_down(router, "fallback1")
    assert shell.complete_json("s", "u") == {"ok": True}
    usage = shell.usage()
    assert usage["llm_model"] == "deepseek-y" and usage["llm_endpoint"] == "fallback2"
    assert usage["llm_calls"] == 1 and usage["model_policy"] == "any"
    # 记账不改变共享路由的健康状态：fallback2 成功被记到公共路由上
    assert router.active_endpoint_names() == ["fallback2"]


def test_router_view_same_model_never_switches_model() -> None:
    from impl.projects.llm_probe.eval_axes.llm import AxisLlm

    router = _fake_router(("primary", "gpt-x"), ("fallback1", "gpt-x"), ("fallback2", "deepseek-y"))
    client = FakeLlm("judge", lambda *_: {"ok": True}, router=router)
    client.model = "gpt-x"   # 真客户端的 model 就是角色策略模型 = primary 端点的模型
    shell = AxisLlm(client, policy="same_model")
    # 视图只暴露同名模型的端点；中转站不同没关系
    assert [ep.name for ep in client.llm_router.endpoints] == ["primary", "fallback1"]
    _cool_down(router, "primary")
    assert shell.complete_json("s", "u") == {"ok": True}
    assert shell.usage()["llm_endpoint"] == "fallback1" and shell.usage()["llm_model"] == "gpt-x"
    # 同模型端点全部冷却：即便 deepseek-y 健康也不用，直接失败
    _cool_down(router, "fallback1")
    result = shell.complete_json("s", "u")
    assert result["error"] == "llm_request_failed"
    assert "same_model" in result["raw_text"] and "gpt-x" in result["raw_text"]
    assert shell.usage()["llm_model"] == "gpt-x"   # 没有出现过 deepseek-y


def test_same_model_policy_makes_fulfillment_fail_closed(monkeypatch) -> None:
    def router_factory():
        router = _fake_router(("primary", FAKE_MODEL), ("fallback2", "other-model"))
        _cool_down(router, "primary")
        return router

    clients = _install_fake_llm(monkeypatch, judge_status="not_fulfilled", router_factory=router_factory)
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.llm.model_policy", lambda: "same_model")
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(), scenario_id="client_search"))
    fulfillment = results["fulfillment"]
    assert fulfillment.status == STATUS_FAILED
    assert "llm_call_failed" in fulfillment.error
    assert fulfillment.usage["model_policy"] == "same_model"
    assert fulfillment.usage["llm_model"] == ""      # 没有任何一次落到别的模型
    assert results["carryability"].status == STATUS_BLOCKED
    # any 策略下同一情形会用 other-model 顶上
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.llm.model_policy", lambda: "any")
    results = _by_id(run_axes(load_project("llm_probe"), _trace(), _axes(), scenario_id="client_search"))
    assert results["fulfillment"].status == STATUS_SUCCEEDED
    assert results["fulfillment"].usage["llm_model"] == "other-model"
    assert results["fulfillment"].usage["llm_endpoint"] == "fallback2"


def test_model_policy_is_registered_config_with_env_override(tmp_path) -> None:
    from impl.core.config import ConfigError, resolve_runtime_config

    config_path = ROOT_DIR / "impl/config.yaml"
    base_env = (ROOT_DIR / ".env").read_text() if (ROOT_DIR / ".env").exists() else ""
    plain = tmp_path / "plain.env"; plain.write_text(base_env)
    assert resolve_runtime_config(config_path=config_path, dotenv_path=plain, environ={}).eval_axes.model_policy == "any"
    strict = tmp_path / "strict.env"; strict.write_text(base_env + "\nEVAL_AXES_MODEL_POLICY=same_model\n")
    resolved = resolve_runtime_config(config_path=config_path, dotenv_path=strict, environ={})
    assert resolved.eval_axes.model_policy == "same_model"
    assert resolved.source_for("eval_axes.model_policy").name == "EVAL_AXES_MODEL_POLICY"
    bad = tmp_path / "bad.env"; bad.write_text(base_env + "\nEVAL_AXES_MODEL_POLICY=whatever\n")
    with pytest.raises(ConfigError, match="eval_axes.model_policy"):
        resolve_runtime_config(config_path=config_path, dotenv_path=bad, environ={})


# ---------------------------------------------------------------- 判后 pass：钩子、core 装载、_run_payload、表格


def _preset_with_axes(*, enabled: bool = True) -> dict:
    return {"client_search": {
        "capability": CAPABILITY,
        "axes": [
            {"type": "fulfillment", "enabled": enabled, "description": CAPABILITY},
            {"type": "carryability", "enabled": enabled, "description": BOUNDARY},
        ],
    }}


def test_run_for_trace_is_noop_without_enabled_boxes(monkeypatch) -> None:
    from impl.projects.llm_probe.eval_axes import run_for_trace

    spec = load_project("llm_probe")
    clients = _install_fake_llm(monkeypatch)
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.load_capability_map", lambda _p: {"client_search": {"capability": CAPABILITY}})
    assert run_for_trace(spec, _trace()) is None
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.load_capability_map", lambda _p: _preset_with_axes(enabled=False))
    assert run_for_trace(spec, _trace()) is None
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.load_capability_map", lambda _p: {})
    assert run_for_trace(spec, _trace()) is None
    assert clients == []   # 一次模型调用都没有


def test_run_for_trace_runs_enabled_boxes(monkeypatch) -> None:
    from impl.projects.llm_probe.eval_axes import run_for_trace

    _install_fake_llm(monkeypatch, judge_status="not_fulfilled", carry="no")
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.load_capability_map", lambda _p: _preset_with_axes())
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.validate.load_capability_map", lambda _p: _preset_with_axes())
    report = run_for_trace(load_project("llm_probe"), _trace())
    assert report["scenario_id"] == "client_search"
    assert [r["axis_id"] for r in report["results"]] == ["fulfillment", "carryability"]
    assert report["results"][0]["summary"]["text"].startswith("not_fulfilled")
    assert report["results"][1]["summary"]["items"][0]["value"] == PLACEMENT_CANNOT


def test_core_loader_is_declarative_and_isolated(monkeypatch) -> None:
    from impl.core.eval_axes import eval_axes_report

    trace = _trace()
    judge = object()
    # 没有 eval_axes 模块的项目：什么都不发生
    assert eval_axes_report(load_project("client_search"), trace, judge) is None
    # 没有 judge 的 run 不做判后 pass
    assert eval_axes_report(load_project("llm_probe"), trace, None) is None
    # 钩子抛异常 → 只记 error，不外抛
    def boom(_spec, _trace):
        raise RuntimeError("axes exploded")
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.run_for_trace", boom)
    assert eval_axes_report(load_project("llm_probe"), trace, judge) == {"error": "RuntimeError: axes exploded"}
    # 无效配置（carryability 启用但 fulfillment 未启用）同样只落 error
    monkeypatch.undo()
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.load_capability_map", lambda _p: {"client_search": {
        "capability": CAPABILITY,
        "axes": [{"type": "carryability", "enabled": True, "description": BOUNDARY}],
    }})
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.validate.load_capability_map", lambda _p: {"client_search": {
        "capability": CAPABILITY,
        "axes": [{"type": "carryability", "enabled": True, "description": BOUNDARY}],
    }})
    report = eval_axes_report(load_project("llm_probe"), trace, judge)
    assert "依赖 fulfillment" in report["error"]


def test_run_payload_attaches_eval_axes_without_touching_run_status(monkeypatch) -> None:
    from impl.core import pipeline
    from impl.core.schema import JudgeResult

    monkeypatch.setattr(pipeline, "live_carrier_report", lambda *_a, **_k: None)   # 旧轴2不在本测试范围
    fake_report = {"run_id": "axes-x", "scenario_id": "client_search", "results": [{
        "axis_id": "fulfillment", "type_id": "fulfillment", "title": "能力兑现", "status": "succeeded",
        "verdict": "not_fulfilled", "summary": {"text": "not_fulfilled · blocking=[x]", "items": [{"key": "x", "value": "not_fulfilled", "reason": "r"}]},
    }]}
    monkeypatch.setattr(pipeline, "eval_axes_report", lambda *_a, **_k: fake_report)
    judge = JudgeResult(trace_id="probe-trace-1", project_id="llm_probe", overall_fulfillment={"status": "not_fulfilled"})
    run = pipeline._run_payload(_trace(), judge, None, case_id="case-1")
    assert run["eval_axes"] is fake_report
    assert "run_status" not in run and "error" not in run

    monkeypatch.setattr(pipeline, "eval_axes_report", lambda *_a, **_k: {"error": "RuntimeError: axes exploded"})
    run = pipeline._run_payload(_trace(), judge, None, case_id="case-1")
    assert run["eval_axes"] == {"error": "RuntimeError: axes exploded"}
    assert "run_status" not in run and "error" not in run

    monkeypatch.setattr(pipeline, "eval_axes_report", lambda *_a, **_k: None)
    run = pipeline._run_payload(_trace(), judge, None, case_id="case-1")
    assert "eval_axes" not in run   # 没启用框：run 的键集与改动前一致


def test_table_row_carries_eval_axes_summary_through_compact_run() -> None:
    from impl.core.schema import JudgeResult, normalize_trace_table_row, to_dict
    from impl.core.table_view import build_trace_table_row_from_run
    from impl.server.service import compact_run

    judge = JudgeResult(trace_id="probe-trace-1", project_id="llm_probe", overall_fulfillment={"status": "not_fulfilled"})
    run = {
        "trace": _trace(), "judge": judge, "attribute": None, "case_id": "case-1",
        "eval_axes": {"run_id": "axes-x", "scenario_id": "client_search", "results": [
            {"axis_id": "fulfillment", "type_id": "fulfillment", "title": "能力兑现", "status": "succeeded", "verdict": "not_fulfilled",
             "summary": {"text": "not_fulfilled · blocking=[x]", "items": [{"key": "x", "value": "not_fulfilled", "reason": "r", "blocking": True}]}},
            {"axis_id": "carryability", "type_id": "carryability", "title": "承载性", "status": "not_applicable", "verdict": None,
             "summary": {"text": "fulfillment=fulfilled，不在筛选范围 [not_fulfilled]，不判", "items": []}},
        ]},
    }
    compact = compact_run(run)
    assert compact["eval_axes"] is run["eval_axes"]
    rows = compact["table_row"]["eval_axes_summary"]
    assert [(r["axis_id"], r["status"], r["verdict"]) for r in rows] == [("fulfillment", "succeeded", "not_fulfilled"), ("carryability", "not_applicable", None)]
    assert rows[0]["title"] == "能力兑现"
    assert rows[0]["text"] == "not_fulfilled · blocking=[x]"
    assert rows[0]["items"][0]["value"] == "not_fulfilled"
    # 整体失败折成一条伪轴
    failed = build_trace_table_row_from_run({"trace": _trace(), "judge": judge, "eval_axes": {"error": "RuntimeError: boom"}})
    assert failed.eval_axes_summary == [{"axis_id": "", "title": "扩展评估轴", "status": "failed", "verdict": None, "text": "RuntimeError: boom", "items": []}]
    # 没有 eval_axes 的 run：字段为空列表，其他字段不受影响
    plain = build_trace_table_row_from_run({"trace": _trace(), "judge": judge})
    assert plain.eval_axes_summary == []
    # 反序列化保留
    restored = normalize_trace_table_row(to_dict(compact["table_row"]))
    assert restored.eval_axes_summary == rows


# ---------------------------------------------------------------- 类型层约束


def test_axis_type_requires_references_inside_depend_on() -> None:
    with pytest.raises(ValueError, match="depend_on"):
        AxisType(
            type_id="bad",
            title="b",
            summary="b",
            verdict_scope="axis",
            verdict_enum=(Verdict("ok", "ok"),),
            depend_on=(),
            trigger_when=When(axis="fulfillment", verdict_in=("not_fulfilled",)),
            inputs=(),
            output_fields=("verdict",),
            verdict_path="verdict",
            scenario_fields=(),
            limits=ExecutionLimits(),
            run=lambda *_: RunOutcome(output={}),
        )


def test_axis_input_from_upstream_must_project_named_fields() -> None:
    with pytest.raises(ValueError, match="fields"):
        Input("fulfillment", source="axis.fulfillment.output")
    with pytest.raises(ValueError, match="source"):
        Input("answer", source="sample.answer")


# ---------------------------------------------------------------- 加载期校验


def test_validate_rejects_enabled_downstream_without_enabled_upstream() -> None:
    report = validate_scenario_axes([ScenarioAxis("carryability", True, BOUNDARY)])
    assert any("依赖 fulfillment" in item for item in report.errors)
    report = validate_scenario_axes(_axes(fulfillment_enabled=False))
    assert any("未启用" in item for item in report.errors)
    assert validate_scenario_axes(_axes()).ok


def test_validate_rejects_unknown_type_and_bad_material_ref() -> None:
    report = validate_scenario_axes([ScenarioAxis("fluency", True, "流畅度")])
    assert any("未注册" in item for item in report.errors)
    report = validate_scenario_axes([ScenarioAxis("fulfillment", True, "见 {material://llm_probe/no-such-material}")])
    assert any("资料引用无效" in item for item in report.errors)


def test_parse_axes_shape_rules() -> None:
    assert parse_axes(None) == []
    axes = parse_axes([{"type": "fulfillment", "enabled": True, "description": CAPABILITY}])
    assert axes == [ScenarioAxis("fulfillment", True, CAPABILITY)]
    with pytest.raises(ValueError, match="只允许一个"):
        parse_axes([
            {"type": "fulfillment", "description": "a"},
            {"type": "fulfillment", "description": "b"},
        ])
    with pytest.raises(ValueError, match="description"):
        parse_axes([{"type": "fulfillment", "description": "   "}])
    with pytest.raises(ValueError, match="enabled"):
        parse_axes([{"type": "fulfillment", "enabled": "yes", "description": "a"}])


# ---------------------------------------------------------------- 试验入口（API）


def _post(path: str, payload: dict):
    import asyncio

    import httpx

    from impl.server.app import create_app

    async def request():
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(request())


def test_types_endpoint_lists_registered_types() -> None:
    response = _post("/api/eval_axes/types", {"project": "llm_probe"})
    assert response.status_code == 200
    body = response.json()
    assert [item["type_id"] for item in body["types"]] == ["fulfillment", "carryability"]
    other = _post("/api/eval_axes/types", {"project": "client_search"})
    assert other.status_code == 500
    assert "llm_probe" in other.json()["error"]


def test_run_endpoint_reads_axes_from_capability_preset(monkeypatch) -> None:
    _install_fake_llm(monkeypatch, judge_status="not_fulfilled", carry="no")
    monkeypatch.setattr(
        "impl.projects.llm_probe.eval_axes.validate.load_capability_map",
        lambda _project: {"client_search": {
            "capability": CAPABILITY,
            "axes": [
                {"type": "fulfillment", "enabled": True, "description": CAPABILITY},
                {"type": "carryability", "enabled": True, "description": BOUNDARY},
            ],
        }},
    )
    from impl.core.schema import to_dict

    response = _post("/api/eval_axes/run", {"project": "llm_probe", "trace": to_dict(_trace()), "run_id": "axes-api"})
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["run_id"] == "axes-api"
    assert body["scenario_id"] == "client_search"
    assert [item["type"] for item in body["axes"]] == ["fulfillment", "carryability"]
    statuses = {item["axis_id"]: item["status"] for item in body["results"]}
    assert statuses == {"fulfillment": STATUS_SUCCEEDED, "carryability": STATUS_SUCCEEDED}
    assert body["results"][0]["verdict"] == "not_fulfilled"
    assert body["results"][1]["output"]["placements"][0]["placement"] == PLACEMENT_CANNOT


def test_run_endpoint_rejects_missing_trace_and_unknown_preset(monkeypatch) -> None:
    assert "trace" in _post("/api/eval_axes/run", {"project": "llm_probe"}).json()["error"]
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.validate.load_capability_map", lambda _project: {})
    from impl.core.schema import to_dict

    response = _post("/api/eval_axes/run", {"project": "llm_probe", "trace": to_dict(_trace())})
    assert response.status_code == 500
    assert "client_search" in response.json()["error"]


def test_capability_entry_keeps_axes_and_rejects_bad_shape() -> None:
    clean = validate_entry("policy_search", {
        "capability": CAPABILITY,
        "axes": [
            {"type": "fulfillment", "enabled": True, "description": CAPABILITY},
            {"type": "carryability", "enabled": False, "description": BOUNDARY},
        ],
    })
    assert clean["axes"] == [
        {"type": "fulfillment", "enabled": True, "description": CAPABILITY},
        {"type": "carryability", "enabled": False, "description": BOUNDARY},
    ]
    assert "axes" not in validate_entry("policy_search", {"capability": CAPABILITY})
    with pytest.raises(ValueError, match="axes"):
        validate_entry("policy_search", {"capability": CAPABILITY, "axes": {"type": "fulfillment"}})
    with pytest.raises(ValueError, match="description"):
        validate_entry("policy_search", {"capability": CAPABILITY, "axes": [{"type": "fulfillment"}]})
