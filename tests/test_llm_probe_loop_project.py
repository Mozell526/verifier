"""llm_probe_loop 项目接入：轴定义存储、场景框校验、错误码、对外入口（实施 P6、R5、R6）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from impl.core.axis_loop.validate import check_definitions
from impl.core.capability_store import validate_entry
from impl.projects.llm_probe_loop.eval_axes import business_failure, main_axis_upstream
from impl.projects.llm_probe_loop.eval_axes.materials import registry
from impl.projects.llm_probe_loop.eval_axes.registry import AXIS_TYPES, definitions, describe_axis_types
from impl.projects.llm_probe_loop.eval_axes.validate import validate_scenario_entry


def test_phase_one_definitions_load_clean():
    defs = definitions()
    assert list(defs.axes) == ["expectations", "blocking", "claims", "truthfulness", "fulfillment", "main_verdict"]
    assert list(defs.shared_tools) == ["search_knowledge"]
    assert check_definitions(defs, registry()) == []
    assert [k for k, a in defs.axes.items() if a.run_mode == "isolated"] == ["expectations", "blocking", "truthfulness"]
    assert AXIS_TYPES["expectations"].role == "analysis" and AXIS_TYPES["fulfillment"].role == "evaluation"
    assert not any(info.requires_business_trace for info in AXIS_TYPES.values())
    assert {d["type"] for d in describe_axis_types()} == set(defs.axes)
    assert main_axis_upstream() == {"expectations", "blocking", "claims", "truthfulness"}


def test_visibility_is_built_into_the_definitions():
    defs = definitions()
    delivery = ("case.deliveries", "case.final_output")
    # 交付第一次进主上下文是说法抽取出现时，此时期望已定；需求、blocking 独立运行、材料里没有交付
    assert ("expectations", True) in [(d.axis, d.hard) for d in defs.axes["claims"].depends]
    for key in ("expectations", "blocking"):
        assert not any(m.startswith(delivery) for m in defs.axes[key].materials)
    assert defs.axes["expectations"].code.dispatch is not None


def test_dispatch_splits_requirements_by_turn():
    view = SimpleNamespace(materials={"case.requirements": {"sources": [
        {"id": "t1.user", "turn": "t1", "side": "want", "component": "user"},
        {"id": "t2.history.0", "turn": "t2", "side": "history", "component": "history"},
        {"id": "t2.user", "turn": "t2", "side": "want", "component": "user"},
        {"id": "scenario.criterion", "turn": "case", "side": "want", "component": "criterion"}], "missing": []}})
    parts = definitions().axes["expectations"].code.dispatch(view)
    assert parts == [{"id": "t1", "materials": ["case.requirements.sources[id=t1.user]"]},
                     {"id": "t2", "materials": ["case.requirements.sources[id=t2.history.0,t2.user,scenario.criterion]"]}]


def test_scenario_entry_needs_hard_dependencies():
    with pytest.raises(ValueError, match="硬依赖 expectations"):
        validate_scenario_entry({"axes": [{"type": "fulfillment", "enabled": True, "description": ""}]}, owner="x")
    axes = validate_scenario_entry({"axes": [{"type": k, "enabled": True, "description": ""}
                                             for k in ("expectations", "blocking", "claims", "fulfillment", "main_verdict")]}, owner="x")
    assert axes.enabled == ["expectations", "blocking", "claims", "fulfillment", "main_verdict"]


def _trace(output_text="", fallback_reason=""):
    fallbacks = [SimpleNamespace(quality_flags=["live_http_error"], reason=fallback_reason)] if fallback_reason else []
    return SimpleNamespace(fallbacks=fallbacks, extracted_output={"output_text": output_text})


def test_only_registered_error_codes_count_as_business_failure():
    entry = validate_entry("s", {"capability": "x", "business_failure": {"http_status": [503], "body": {"pointer": "/code", "values": ["E1"]}}})
    assert business_failure.matched(_trace(fallback_reason='HTTP 503: {"msg": "busy"}'), entry).startswith("被测系统返回 HTTP 503")
    assert business_failure.matched(_trace(fallback_reason='HTTP 500: {"msg": "x"}'), entry) == ""   # 没登记的非 2xx 照常评测
    assert "错误码 /code=E1" in business_failure.matched(_trace('{"code": "E1", "data": null}'), entry)
    assert business_failure.matched(_trace('{"code": "OK"}'), entry) == ""
    assert business_failure.matched(_trace(fallback_reason="HTTP 503: x"), {}) == ""                   # 没配就不判失败
    with pytest.raises(ValueError):
        validate_entry("s", {"capability": "x", "business_failure": {"http_status": ["503"]}})
