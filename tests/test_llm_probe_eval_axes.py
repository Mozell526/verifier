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


def test_registry_exposes_types_with_frozen_enums() -> None:
    described = {item["type_id"]: item for item in describe_axis_types()}
    assert set(described) == {"fulfillment", "carryability", "truthfulness"}
    assert [v["value"] for v in described["fulfillment"]["verdict_enum"]] == ["fulfilled", "not_fulfilled", "not_evaluable"]
    assert [v["value"] for v in described["carryability"]["verdict_enum"]] == ["做不了", "做错了", "说不清"]
    assert described["fulfillment"]["verdict_scope"] == "axis"
    assert described["carryability"]["verdict_scope"] == "item"
    assert described["carryability"]["depend_on"] == [{"type_id": "fulfillment", "optional": False}]
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
    monkeypatch.setattr("impl.projects.llm_probe.eval_axes.llm.model_policy", lambda: "any")
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


def test_runner_hands_adapter_a_deadline_from_limits_seconds(monkeypatch) -> None:
    """seconds 是协作式上限：运行器算好截止时刻交给 run()，adapter 在开下一次调用前查；到点报 failed 且写明超时。"""
    seen: dict[str, Any] = {}

    def slow(_inputs, _axis, runtime) -> RunOutcome:
        seen["deadline"] = runtime.deadline
        monkeypatch.setattr(runner_module.time, "monotonic", lambda: runtime.deadline + 1)
        runtime.ensure_time_left("第二次调用")
        raise AssertionError("到点后不该继续")

    custom = AxisType(
        type_id="custom", title="c", summary="c", verdict_scope="axis", verdict_enum=(Verdict("ok", "ok"),),
        depend_on=(), trigger_when=None, inputs=(Input("trace", source="sample.trace"),), output_fields=("verdict",),
        verdict_path="verdict", scenario_fields=(Field("description"),), limits=ExecutionLimits(seconds=5), run=slow,
    )
    monkeypatch.setattr(runner_module, "get_axis_type", lambda type_id: custom if type_id == "custom" else get_axis_type(type_id))
    result = run_axes(load_project("llm_probe"), _trace(), [ScenarioAxis("custom", True, "x")], scenario_id="s")[0]
    assert seen["deadline"] is not None
    assert result.status == STATUS_FAILED
    assert "超时（上限 5s）" in result.error and "第二次调用" in result.error
    assert result.usage["timed_out"] is True


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
    base_env = "\n".join(line for line in base_env.splitlines() if not line.startswith("EVAL_AXES_MODEL_POLICY="))
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
        "stage_timings": {"live_ms": 6200, "judge_ms": 40100, "eval_axes_ms": 105000},
        "eval_axes": {"run_id": "axes-x", "scenario_id": "client_search", "results": [
            {"axis_id": "fulfillment", "type_id": "fulfillment", "title": "能力兑现", "status": "succeeded", "verdict": "not_fulfilled",
             "usage": {"llm_calls": 1, "tool_calls": 0, "elapsed_ms": 45000, "llm_model": "m"},
             "summary": {"text": "not_fulfilled · blocking=[x]", "items": [{"key": "x", "value": "not_fulfilled", "reason": "r", "blocking": True}]}},
            {"axis_id": "carryability", "type_id": "carryability", "title": "承载性", "status": "not_applicable", "verdict": None,
             "summary": {"text": "fulfillment=fulfilled，不在筛选范围 [not_fulfilled]，不判", "items": []}},
            {"axis_id": "truthfulness", "type_id": "truthfulness", "title": "真实性", "status": "succeeded", "verdict": None,
             "usage": {"llm_calls": 3, "tool_calls": 11, "elapsed_ms": 60400},
             "summary": {"text": "$refuted…", "items": [{"key": "c1", "value": "refuted", "reason": "r1"}, {"key": "c2", "value": "verified", "reason": "r2"}, {"key": "c3", "value": "refuted", "reason": "r3"}]}},
        ]},
    }
    compact = compact_run(run)
    assert compact["eval_axes"] is run["eval_axes"]
    rows = compact["table_row"]["eval_axes_summary"]
    assert [(r["axis_id"], r["status"], r["verdict"]) for r in rows] == [("fulfillment", "succeeded", "not_fulfilled"), ("carryability", "not_applicable", None), ("truthfulness", "succeeded", None)]
    assert rows[0]["title"] == "能力兑现"
    assert rows[0]["text"] == "not_fulfilled · blocking=[x]"
    assert rows[0]["items"][0]["value"] == "not_fulfilled"
    # 结论令牌 `轴id:值`：轴级一个；item 级按值计数；没跑成用状态；Excel 里「包含 truthfulness:refuted」就能筛。
    assert rows[0]["tokens"] == ["fulfillment:not_fulfilled"]
    assert rows[1]["tokens"] == ["carryability:not_applicable"]
    assert rows[2]["tokens"] == ["truthfulness:refuted×2", "truthfulness:verified×1"]
    # 耗时与调用数一起搬到表格层，主表/导出不用再翻 usage。
    assert (rows[0]["elapsed_ms"], rows[0]["llm_calls"], rows[0]["tool_calls"], rows[0]["llm_model"]) == (45000, 1, 0, "m")
    assert (rows[2]["elapsed_ms"], rows[2]["tool_calls"]) == (60400, 11)
    assert compact["table_row"]["stage_timings"] == {"live_ms": 6200, "judge_ms": 40100, "eval_axes_ms": 105000}
    # 整体失败折成一条伪轴
    failed = build_trace_table_row_from_run({"trace": _trace(), "judge": judge, "eval_axes": {"error": "RuntimeError: boom"}})
    assert failed.eval_axes_summary == [{"axis_id": "", "title": "扩展评估轴", "status": "failed", "verdict": None, "text": "RuntimeError: boom", "items": []}]
    # 没有 eval_axes 的 run：字段为空列表，其他字段不受影响
    plain = build_trace_table_row_from_run({"trace": _trace(), "judge": judge})
    assert plain.eval_axes_summary == [] and plain.stage_timings == {}
    from impl.core.table_view import eval_axis_tokens
    assert eval_axis_tokens("truthfulness", "disabled", None, []) == []
    assert eval_axis_tokens("truthfulness", "succeeded", None, []) == ["truthfulness:empty"]
    assert eval_axis_tokens("truthfulness", "failed", None, [{"value": "verified"}]) == ["truthfulness:failed"]
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
    assert [item["type_id"] for item in body["types"]] == ["fulfillment", "carryability", "truthfulness"]
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


@pytest.mark.parametrize('upstream_state', ['missing', 'disabled', 'succeeded', 'failed'])
def test_optional_dependency_orders_projects_and_omits_failed_output(monkeypatch, upstream_state):
    from dataclasses import replace
    from impl.projects.llm_probe.eval_axes.types import Dependency, AxisSummary
    seen = []
    def upstream_run(inputs, axis, runtime):
        seen.append('upstream')
        return RunOutcome({'value': 'fulfilled'}, AxisSummary('上游'), failed=upstream_state == 'failed')
    def downstream_run(inputs, axis, runtime):
        seen.append(inputs)
        return RunOutcome({'value': 'fulfilled'}, AxisSummary('下游'))
    template = get_axis_type('fulfillment')
    upstream = replace(template, type_id='upstream', depend_on=(), inputs=(), output_fields=('value',), verdict_path='value', run=upstream_run)
    downstream = replace(upstream, type_id='downstream', depend_on=(Dependency('upstream', optional=True),), inputs=(Input('evidence', 'axis.upstream.output', fields=('value',), required=False),), run=downstream_run)
    registry = {'upstream': upstream, 'downstream': downstream}
    monkeypatch.setattr(runner_module, 'get_axis_type', registry.__getitem__)
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.validate.AXIS_TYPES', registry)
    axes = [ScenarioAxis('downstream', True, '下游')]
    if upstream_state != 'missing':
        axes.append(ScenarioAxis('upstream', upstream_state != 'disabled', '上游'))
    assert validate_scenario_axes(axes).ok
    results = _by_id(run_axes(None, _trace(), axes, scenario_id='test'))
    result = results['downstream']
    assert result.status == 'succeeded'
    assert seen[-1] == ({'evidence': {'value': 'fulfilled'}} if upstream_state == 'succeeded' else {})
    if upstream_state in ('failed', 'succeeded'):
        assert seen[0] == 'upstream'
    assert result.trigger_decision['upstream']['upstream'] == upstream_state
    assert ('（upstream未完成，未纳入）' in result.summary['text']) == (upstream_state == 'failed')


def test_optional_dependency_rejects_required_input_and_trigger():
    from dataclasses import replace
    from impl.projects.llm_probe.eval_axes.types import Dependency
    template = get_axis_type('carryability')
    with pytest.raises(ValueError, match='required=False'):
        replace(template, depend_on=(Dependency('fulfillment', True),), trigger_when=None)
    with pytest.raises(ValueError, match='trigger_when.*可选'):
        replace(template, depend_on=(Dependency('fulfillment', True),), inputs=())


@pytest.fixture
def fake_es(monkeypatch):
    from dataclasses import replace
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from impl.core.config import get_runtime_config
    from impl.core.config_schema import EvalAxesEsConfig
    requests = []
    documents = {'doc1': {'clause': '犹豫期二十日', 'nested': {'title': '保障条款'}, 'tags': ['保障', '保险']}}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.respond()
        def do_POST(self):
            self.respond()
        def respond(self):
            from urllib.parse import unquote
            body = json.loads(self.rfile.read(int(self.headers['Content-Length']))) if self.headers.get('Content-Length') else None
            requests.append((self.command, self.path, body, self.headers.get('Authorization')))
            status = 200
            if self.path == '/kb_policy/_mapping':
                result = {'kb_policy': {'mappings': {'properties': {'clause': {'type': 'text', 'fields': {'raw': {'type': 'keyword'}}}, 'nested': {'properties': {'title': {'type': 'text'}}}, 'tags': {'type': 'keyword'}}}}}
            elif self.path == '/kb_policy/_count':
                result = {'count': len(documents)}
            elif self.path == '/kb_policy/_settings/index.uuid':
                result = {'kb_policy': {'settings': {'index': {'uuid': 'uuid-test'}}}}
            elif self.path == '/kb_policy/_search':
                asked = json.dumps(body, ensure_ascii=False)
                hits = [] if '不存在' in asked else [{'_id': 'doc1', '_score': 2.0, '_source': documents.get('doc1', {}), 'highlight': {'clause': ['犹豫期二十日']}}]
                result = {'hits': {'hits': hits}}
            elif self.path.startswith('/kb_policy/_doc/') and unquote(self.path.split('/_doc/')[1]) in documents:
                result = {'found': True, '_source': documents[unquote(self.path.split('/_doc/')[1])]}
            else:
                status, result = 404, {'error': 'missing'}
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = get_runtime_config()
    es = EvalAxesEsConfig(enabled=True, base_url=f'http://127.0.0.1:{server.server_port}', api_key='test-key')
    monkeypatch.setattr('impl.core.config._RUNTIME_CONFIG', replace(config, eval_axes=replace(config.eval_axes, es=es)))
    # Consumers use the resolver accessor, with the same typed config as production.
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.sources.es_client.get_runtime_config', lambda: replace(config, eval_axes=replace(config.eval_axes, es=es)))
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.sources.get_runtime_config', lambda: replace(config, eval_axes=replace(config.eval_axes, es=es)))
    try:
        yield requests, documents
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_es_tools_catalog_receipts_scope_and_quote_readback(fake_es):
    from impl.projects.llm_probe.eval_axes.sources import expand_sources, build_tools
    from impl.projects.llm_probe.eval_axes.sources.es_tools import EsTools
    requests, documents = fake_es
    text, catalog = expand_sources('核对 {es://kb_policy} 条款。')
    assert '{es://' not in text
    assert catalog[0]['snapshot_id'].startswith('uuid-test@')
    assert catalog[0]['doc_count'] == 1
    receipts = []
    tools = {t.name: t.entrypoint for t in build_tools(catalog, receipts)}
    outline = tools['es_outline'](index='kb_policy')
    assert [f['name'] for f in outline['fields'] if f['full_text']] == ['clause', 'nested.title']
    search = tools['es_search'](index='kb_policy', query='犹豫期 康宁')
    assert search['hits'][0]['locator'] == 'doc1#clause'
    assert search['hits'][0]['matched'] == ['犹豫期']
    sent = next(r for r in requests if r[0] == 'POST')
    # 与 material search 同语义：每词 phrase（子串）OR keyword 通配，词间 OR；不能把整串交给 ES 按单字 OR。
    should = sent[2]['query']['bool']['should']
    assert sent[2]['query']['bool']['minimum_should_match'] == 1
    assert [c['multi_match'] for c in should if 'multi_match' in c] == [
        {'query': '犹豫期', 'fields': ['clause', 'nested.title'], 'type': 'phrase'},
        {'query': '康宁', 'fields': ['clause', 'nested.title'], 'type': 'phrase'},
    ]
    assert [c['wildcard'] for c in should if 'wildcard' in c] == [
        {'tags': {'value': '*犹豫期*', 'case_insensitive': True}},
        {'tags': {'value': '*康宁*', 'case_insensitive': True}},
    ]
    assert sent[3] == 'ApiKey test-key'
    empty = tools['es_search'](index='kb_policy', query='不存在的词')
    assert empty['hits'] == [] and '零命中' in empty['note']
    assert tools['es_read'](index='kb_policy', locator='doc1#nested.title')['text'] == '保障条款'
    assert 'clause' in tools['es_read'](index='kb_policy', locator='doc1')['text']
    before = len(requests)
    assert 'error' in tools['es_read'](index='../secret', locator='x')
    assert len(requests) == before
    assert receipts[-1]['returned_locators'] == [] and receipts[-1]['error']
    verifier = EsTools(catalog, receipts)
    assert verifier.verify_quote('kb_policy', 'doc1#clause', '犹豫期二十日')
    assert not verifier.verify_quote('kb_policy', 'doc1#clause', '十五日')
    assert not verifier.verify_quote('kb_policy', 'doc1#absent', '二十日')
    documents.clear()
    assert not verifier.verify_quote('kb_policy', 'doc1#clause', '二十日')
    assert all('tool' in r and 'returned_locators' in r for r in receipts)


def test_es_save_only_validates_format_and_load_rejects_disabled(monkeypatch):
    from dataclasses import replace
    from impl.core.config import get_runtime_config
    config = get_runtime_config()
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.sources.get_runtime_config', lambda: replace(config, eval_axes=replace(config.eval_axes, es=replace(config.eval_axes.es, enabled=False))))
    for marker in ('{es://}', '{es://UPPER}', '{es://x/y}', '{es://x*}', '{es://x'):
        with pytest.raises(ValueError, match='ES 引用'):
            validate_entry('test', {'capability': 'test', 'axes': [{'type': 'carryability', 'enabled': True, 'description': marker}]})
    entry = validate_entry('test', {'capability': 'test', 'axes': [{'type': 'fulfillment', 'enabled': True, 'description': '{es://kb_policy}'}]})
    report = validate_scenario_axes(parse_axes(entry['axes']))
    assert any('ES 数据源未启用' in e for e in report.errors)
    # 未启用的框写了 {es://}：ES 关着也不报错，不拦同预设里已启用的其他轴。
    entry = validate_entry('test', {'capability': 'test', 'axes': [
        {'type': 'truthfulness', 'enabled': False, 'description': '{es://kb_policy}'},
        {'type': 'fulfillment', 'enabled': True, 'description': '按要求回答'},
    ]})
    assert validate_scenario_axes(parse_axes(entry['axes'])).ok


def test_es_configuration_registration_conditional_requirement_and_secrets(tmp_path):
    from impl.core.config import resolve_runtime_config
    dotenv = tmp_path / '.env'
    dotenv.write_text('EVAL_AXES_ES_URL=invalid-url\nEVAL_AXES_ES_API_KEY=secret-test\n')
    config = resolve_runtime_config(dotenv_path=dotenv, environ={})
    assert config.eval_axes.es.enabled is False
    assert config.eval_axes.es.api_key == '' and config.eval_axes.es.base_url == ''
    dotenv.write_text('EVAL_AXES_ES_ENABLED=true\n')
    config = resolve_runtime_config(dotenv_path=dotenv, environ={})
    assert 'eval_axes.es.base_url' in config.missing_required
    dotenv.write_text('EVAL_AXES_ES_ENABLED=true\nEVAL_AXES_ES_URL=http://localhost:9200\nEVAL_AXES_ES_API_KEY=secret-test\n')
    config = resolve_runtime_config(dotenv_path=dotenv, environ={})
    assert config.eval_axes.es.api_key == 'secret-test'
    assert config.source_for('eval_axes.es.api_key').secret
    assert 'secret-test' not in str(config.redacted_dict())


def test_es_read_truncation_and_explicit_fields(fake_es):
    from impl.projects.llm_probe.eval_axes.sources.es_tools import EsTools
    requests, documents = fake_es
    documents['doc1']['long'] = '甲' * 6001
    tools = EsTools([{'source': 'es', 'uri': 'es://kb_policy'}], [])
    result = tools.es_read('kb_policy', 'doc1#long')
    assert result['truncated'] and len(result['text']) == 6000
    assert 'error' in tools.es_search('kb_policy', 'x', ['not_in_mapping'])
    tools.es_search('kb_policy', 'x', ['clause.raw'])
    # 显式指定 fields 时只查这些字段，不再附带 keyword 通配。
    should = requests[-1][2]['query']['bool']['should']
    assert should == [{'multi_match': {'query': 'x', 'fields': ['clause.raw'], 'type': 'phrase'}}]


def test_source_dispatch_preserves_material_entries(monkeypatch):
    from impl.projects.llm_probe.eval_axes.sources import build_tools
    material = {'uri': 'material://p/m', 'project_id': 'p', 'id': 'm'}
    received = []
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.sources.build_material_tools', lambda catalog, recorder: received.extend(catalog) or ['material'])
    assert build_tools([material], []) == ['material']
    assert received[0] is material


def test_carryability_es_quotes_are_read_back(fake_es, monkeypatch):
    from impl.projects.llm_probe.eval_axes.adapters.carryability import BoxBoundaryCarrier
    from impl.projects.llm_probe.eval_axes.types import AxisRuntime
    runtime = AxisRuntime(spec=load_project('llm_probe'), run_id='axes-test', trace_id='axes-test', scenario_id='s', case_id='c')
    carrier = BoxBoundaryCarrier(load_project('llm_probe'), '范围 {es://kb_policy}', runtime)
    monkeypatch.setattr(carrier, '_call_llm', lambda *args: {'carry': 'yes', 'reason': '条款覆盖', 'citations': [{'source': 'es://kb_policy', 'ref': 'doc1#clause', 'note': '犹豫期二十日'}]})
    verdict = carrier.verdict_for({'expectation_id': '查犹豫期'})
    assert verdict.carry == 'yes'
    assert verdict.tool_trail[-1]['tool'] == 'es_read'


def _truth_llm(monkeypatch, extracted, verdicts):
    clients, options = [], []
    remaining = iter(verdicts)
    def script(role, system, user):
        if 'output_text' in json.loads(user):
            return extracted
        value = next(remaining)
        if isinstance(value, Exception):
            raise value
        return value
    def factory(spec, role, **kwargs):
        client = FakeLlm(role, script)
        clients.append(client)
        options.append(kwargs)
        return client
    monkeypatch.setattr('impl.core.llm_client.project_llm_client', factory)
    return clients, options


def _truth_verdict(verdict='refuted', note='犹豫期二十日'):
    return {'verdict': verdict, 'reason': '资料中是二十日', 'citations': [{'source': 'es://kb_policy', 'ref': 'doc1#clause', 'note': note}]}


def test_truthfulness_three_stages_isolated_and_deterministic(fake_es, monkeypatch):
    # 断言 = text + context：上下文片段单独带着，核验时才知道该找哪个产品、哪个条件下的条款；不需要的填 []。
    extracted = {'claims': [{'claim_id': '天数', 'text': '犹豫期十五日', 'context': ['康宁险']}, {'claim_id': '条款', 'text': '保障条款'}]}
    clients, options = _truth_llm(monkeypatch, extracted, [_truth_verdict(), {'verdict': 'unverifiable', 'reason': '没有相关原文', 'citations': []}])
    result = run_axes(load_project('llm_probe'), _trace('康宁险犹豫期十五日；保障条款'), [ScenarioAxis('truthfulness', True, '核对事实 {es://kb_policy}')], scenario_id='s')[0]
    assert result.status == 'succeeded' and result.verdict is None
    assert result.output['coverage'] == {'extracted': 2, 'verified': 0, 'refuted': 1, 'unverifiable': 1}
    assert result.summary['text'].startswith('$refuted\n天数')
    assert [item['key'] for item in result.summary['items']] == ['康宁险：犹豫期十五日', '保障条款']
    assert len(result.summary['items']) == 2 and result.usage['llm_calls'] == 3
    expected_claims = [{'claim_id': '天数', 'text': '犹豫期十五日', 'context': ['康宁险']}, {'claim_id': '条款', 'text': '保障条款', 'context': []}]
    assert result.output['sources'][0]['snapshot_id'].startswith('uuid-test@')
    assert options[0]['tools'] == []
    extraction = json.loads(clients[0].calls[0]['user'])
    assert set(extraction) == {'output_text', 'question'}
    # 提取与核验都是摘抄/查资料，不吃深推理：与生产轴2一致用 low。
    assert all(call.get('reasoning_effort') == 'low' for client in clients for call in client.calls)
    for i in (1, 2):
        payload = json.loads(clients[i].calls[0]['user'])
        # 首轮就带知识源骨架，模型不必再花一次工具调用 outline，也一开始就知道字段在哪。
        assert set(payload) == {'claim', 'description', 'catalog', 'outline', 'feedback'}
        assert payload['outline'][0]['index'] == 'kb_policy'
        assert [f['name'] for f in payload['outline'][0]['fields'] if f['type'] == 'keyword'] == ['clause.raw', 'tags']
        assert payload['claim'] == expected_claims[i - 1]
        assert 'question' not in payload and 'output_text' not in payload
        assert options[i]['tool_call_limit'] == 16
        assert {tool.name for tool in options[i]['tools']} == {'es_outline', 'es_search', 'es_read'}


def test_truthfulness_extraction_repairs_schema_block_once(monkeypatch):
    """提取被结构校验阻断（如模型把 schema 里的 required 当字段输出）时，与生产 judge 一样只做一次带具体错误的格式修复。"""
    attempts = []

    def script(role, system, user):
        attempts.append(user)
        if len(attempts) == 1:
            raise ValueError('额外字段不允许：required')
        assert '上次输出不符合要求' in user and 'required' in user
        return {'claims': []}

    clients = []
    def factory(spec, role, **kwargs):
        client = FakeLlm(role, script)
        clients.append(client)
        return client
    monkeypatch.setattr('impl.core.llm_client.project_llm_client', factory)
    result = run_axes(None, _trace('答复'), [ScenarioAxis('truthfulness', True, '核对事实')], scenario_id='s')[0]
    assert result.status == 'succeeded' and len(attempts) == 2
    assert result.usage['llm_calls'] == 2


@pytest.mark.parametrize('claims,success', [([], True), ([{'claim_id': 'fake', 'text': '原文中不存在'}], False), ([{'claim_id': 'x', 'text': '答 复'}], False),
                                            ([{'claim_id': 'x', 'text': '答复', 'context': ['原文中不存在']}], False)])
def test_truthfulness_empty_and_fabricated_claims(monkeypatch, claims, success):
    clients, options = _truth_llm(monkeypatch, {'claims': claims}, [])
    result = run_axes(None, _trace('答复'), [ScenarioAxis('truthfulness', True, '核对事实')], scenario_id='s')[0]
    assert result.status == ('succeeded' if success else 'failed')
    assert len(clients) == 1
    assert result.output['claims'] == []
    if success:
        assert result.summary['text'] == '回答不含可核验的事实断言'
    else:
        assert result.output['errors'] and result.usage['llm_calls'] == 2


def test_truthfulness_context_must_not_leak_other_claims(monkeypatch):
    """context 带了别条断言的值 = 把整句塞回来，隔离失效，程序打回；给一次带具体错误的修复机会，仍偷懒则 failed。"""
    answer = '安心医疗险的等待期为三十日，免赔额为一万元。'
    lazy = {'claims': [
        {'claim_id': '1', 'text': '等待期为三十日', 'context': [answer]},
        {'claim_id': '2', 'text': '免赔额为一万元', 'context': ['安心医疗险']},
    ]}
    attempts = []

    def script(role, system, user):
        attempts.append(user)
        return lazy

    monkeypatch.setattr('impl.core.llm_client.project_llm_client', lambda spec, role, **kwargs: FakeLlm(role, script))
    result = run_axes(None, _trace(answer), [ScenarioAxis('truthfulness', True, '核对事实')], scenario_id='s')[0]
    assert result.status == 'failed' and '含了断言 2 的值' in result.summary['text']
    assert len(attempts) == 2 and '含了断言 2 的值' in attempts[1]
    assert result.output['claims'] == [] and result.usage['llm_calls'] == 2


@pytest.mark.parametrize('invalid', [_truth_verdict(note='十五日'), {'verdict': 'verified', 'reason': '支持', 'citations': []}, {'error': 'llm down'}])
def test_truthfulness_retries_invalid_citations_then_succeeds(fake_es, monkeypatch, invalid):
    clients, _ = _truth_llm(monkeypatch, {'claims': [{'claim_id': 'days', 'text': '十五日'}]}, [invalid, _truth_verdict('verified')])
    result = run_axes(None, _trace('十五日'), [ScenarioAxis('truthfulness', True, '{es://kb_policy}')], scenario_id='s')[0]
    assert result.status == 'succeeded'
    assert result.output['coverage']['verified'] == 1
    assert result.usage['llm_calls'] == 3
    assert json.loads(clients[2].calls[0]['user'])['feedback']


def test_truthfulness_exhaustion_retains_partial_results(fake_es, monkeypatch):
    clients, _ = _truth_llm(monkeypatch, {'claims': [{'claim_id': 'one', 'text': '十五日'}, {'claim_id': 'two', 'text': '二十日'}]}, [_truth_verdict(), _truth_verdict(note='伪造'), _truth_verdict(note='伪造')])
    result = run_axes(None, _trace('十五日二十日'), [ScenarioAxis('truthfulness', True, '{es://kb_policy}')], scenario_id='s')[0]
    assert result.status == 'failed' and result.verdict is None
    assert len(result.output['claims']) == len(result.summary['items']) == 1
    assert result.output['errors'][0]['claim_id'] == 'two'
    # 每条断言最多 2 次：首轮上下文已经把骨架和检索语义给全，重试是兜底不是常态。
    assert result.output['errors'][0]['attempts'] == 2
    assert len(clients) == 4


def test_truthfulness_tool_errors_cannot_be_unverifiable(fake_es, monkeypatch):
    from impl.projects.llm_probe.eval_axes.adapters.truthfulness import _verify_result
    with pytest.raises(ValueError, match='工具调用失败'):
        _verify_result({'verdict': 'unverifiable', 'reason': '没有找到', 'citations': []}, [], '', [{'error': 'HTTP 500'}])


@pytest.mark.parametrize('output_text', ['plain answer', '{"conditions": []}', ''])
def test_fulfillment_truth_adds_exactly_two_prompt_extras(output_text):
    from copy import deepcopy
    from impl.projects.llm_probe.eval_axes.adapters.fulfillment import build_context
    spec, trace = load_project('llm_probe'), _trace(output_text)
    base = build_context(spec, trace, CAPABILITY)
    truth = {'claims': [{'claim_id': 'days', 'text': '十五日', 'context': ['康宁险'], **_truth_verdict(), 'private': 'must not leak'}], 'coverage': {'refuted': 1}}
    original = deepcopy(truth)
    enriched = build_context(spec, trace, CAPABILITY, truth)
    assert enriched['user_prompt_extras'].pop('truthfulness') == {'claims': [{k: v for k, v in truth['claims'][0].items() if k != 'private'}]}
    assert enriched['system_prompt_extras'].pop() == (
        '## 真实性核验结果\n'
        '上游已对回答中的事实断言逐条核验。`refuted` 的断言视为事实错误，据此判相关期望 not_fulfilled；'
        '`unverifiable` 不构成失败依据；不要重复核验，也不要发明核验结果里没有的断言。'
    )
    assert enriched == base
    assert truth == original


def test_truthfulness_flows_to_fulfillment_but_not_carryability(fake_es, monkeypatch):
    clients = []
    def script(role, system, user):
        if role == 'truthfulness':
            if 'output_text' in json.loads(user):
                return {'claims': [{'claim_id': 'days', 'text': '十五日'}]}
            return _truth_verdict()
        if role == 'judge':
            assert '## 真实性核验结果' in system
            assert 'truthfulness' in user and '十五日' in user
            return _judge_payload('not_fulfilled')
        assert 'truthfulness' not in user and '十五日' not in user
        return _carrier_payload('no')
    def factory(spec, role, **kwargs):
        client = FakeLlm(role, script)
        clients.append(client)
        return client
    monkeypatch.setattr('impl.core.llm_client.project_llm_client', factory)
    results = run_axes(load_project('llm_probe'), _trace('十五日'), _axes() + [ScenarioAxis('truthfulness', True, '{es://kb_policy}')], scenario_id='s')
    assert [r.axis_id for r in results] == ['truthfulness', 'fulfillment', 'carryability']
    assert all(r.status == 'succeeded' for r in results)
    assert set(results[1].inputs_used) == {'trace', 'truth'}
    assert set(results[2].inputs_used) == {'fulfillment'}


def test_truthfulness_small_material_has_tools_and_source_snapshot(monkeypatch):
    import impl.core.materials_store as ms
    from impl.projects.llm_probe.eval_axes.sources import expand_sources
    token = '{material://llm_probe/client-search-match-rule}'
    content = ms.read_content('llm_probe', 'client-search-match-rule')
    quote = next(line for line in content.splitlines() if line.strip())
    clients, options = _truth_llm(monkeypatch, {'claims': [{'claim_id': '规则', 'text': quote}]}, [{'verdict': 'verified', 'reason': '原文支持', 'citations': [{'source': token[1:-1], 'ref': 'L1-L10', 'note': quote}]}])
    result = run_axes(None, _trace(quote), [ScenarioAxis('truthfulness', True, token)], scenario_id='s')[0]
    assert result.status == 'succeeded'
    assert result.output['sources'][0]['snapshot_id']
    assert {tool.name for tool in options[1]['tools']} == {'material_outline', 'material_search', 'material_read'}
    assert expand_sources(token)[1] == []  # 承载性原有小资料内联行为不变


def test_es_disabled_cli_ignores_invalid_url_even_when_env_enables(tmp_path):
    from impl.core.config import resolve_runtime_config
    dotenv = tmp_path / '.env'
    dotenv.write_text('EVAL_AXES_ES_ENABLED=true\nEVAL_AXES_ES_URL=invalid\n')
    config = resolve_runtime_config(dotenv_path=dotenv, environ={}, cli_overrides={'eval_axes.es.enabled': False, 'eval_axes.es.base_url': 'invalid'})
    assert not config.eval_axes.es.enabled and config.eval_axes.es.base_url == ''


def test_es_loading_rejects_enabled_but_unconfigured_source(monkeypatch):
    from dataclasses import replace
    from impl.core.config import get_runtime_config
    config = get_runtime_config()
    invalid = replace(config, eval_axes=replace(config.eval_axes, es=replace(config.eval_axes.es, enabled=True, base_url='')))
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.sources.get_runtime_config', lambda: invalid)
    monkeypatch.setattr('impl.projects.llm_probe.eval_axes.sources.es_client.get_runtime_config', lambda: invalid)
    report = validate_scenario_axes([ScenarioAxis('truthfulness', True, '{es://kb_policy}')])
    assert any('base_url' in error for error in report.errors)
