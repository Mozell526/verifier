"""axis loop 的定义、材料、校验与验收（spec/alg/axis_loop.md §3–§7；实施 P2、P3）。"""
from __future__ import annotations

import json

import pytest

from impl.core.axis_loop import acceptance, paths
from impl.core.axis_loop.checks import STANDARD, check_params
from impl.core.axis_loop.definitions import Code, parse
from impl.core.axis_loop.materials import Material, MaterialTable, Registry, parse_entry, render
from impl.core.axis_loop.validate import check_definitions, check_scenario
from impl.core.axis_loop.view import CallView, TaskView

TEXT = {"type": "string"}


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props)}


EXPECTATIONS_OUT = obj(
    verdict={"type": "string", "enum": ["complete", "partial"]}, reason=TEXT,
    expectations={"type": "array", "items": obj(expectation_id=TEXT, statement=TEXT)})


def registry():
    return Registry([
        Material("case.deliveries", {"type": "array", "items": obj(turn={"type": "integer"}, text=TEXT)},
                 "每一轮回答", lambda case, ctx: case["deliveries"]),
        Material("scenario.criterion", TEXT, "场景判准", lambda case, ctx: case["criterion"]),
        Material("axis.note", TEXT, "场景对当前轴的描述", lambda case, ctx: f"note for {ctx['axis']}"),
    ])


def store(**axes):
    base = {
        "expectations": {"materials": ["scenario.criterion"], "output": EXPECTATIONS_OUT},
    }
    return {"axes": {**base, **axes}, "shared_tools": {}}


# ---- 路径 -------------------------------------------------------------------------------

def test_path_extract_keeps_shape_and_projects_fields():
    value = {"expectations": [{"expectation_id": "E1", "statement": "s1", "x": 1}, {"expectation_id": "E2", "statement": "s2"}]}
    path = paths.parse("expectations[].{expectation_id, statement}")
    assert paths.extract(value, path) == [{"expectation_id": "E1", "statement": "s1"}, {"expectation_id": "E2", "statement": "s2"}]
    assert paths.values(value, paths.parse("expectations[].expectation_id")) == ["E1", "E2"]


def test_path_schema_check_reports_unknown_field_and_missing_brackets():
    assert paths.check_schema(EXPECTATIONS_OUT, paths.parse("expectations[].statement")) is None
    assert "nope" in paths.check_schema(EXPECTATIONS_OUT, paths.parse("expectations[].nope"))
    assert "[]" in paths.check_schema(EXPECTATIONS_OUT, paths.parse("expectations.statement"))
    assert "投影" in paths.check_schema(EXPECTATIONS_OUT, paths.parse("expectations[].{expectation_id, nope}"))


# ---- 材料 -------------------------------------------------------------------------------

def test_entry_parsing_splits_standard_name_from_path():
    entry = parse_entry("result.expectations.expectations[].{expectation_id, statement}")
    assert (entry.name, entry.axis, str(entry.path)) == ("result.expectations", "expectations", "expectations[].{expectation_id, statement}")
    assert parse_entry("case.deliveries").name == "case.deliveries"
    with pytest.raises(ValueError):
        parse_entry("delivery")


def test_material_table_takes_builtin_and_results_and_renders_missing_upstream():
    table = MaterialTable(registry(), {"deliveries": [{"turn": 1, "text": "回答"}], "criterion": "给出值"})
    table.results["expectations"] = {"expectations": [{"expectation_id": "E1", "statement": "s"}]}
    entries = [parse_entry("scenario.criterion"), parse_entry("result.expectations.expectations[].expectation_id"),
               parse_entry("result.truthfulness"), parse_entry("axis.note")]
    got = table.view(entries, axis_id="fulfillment")
    assert got["result.expectations.expectations[].expectation_id"] == ["E1"]
    assert got["axis.note"] == "note for fulfillment"
    text = render(got)
    assert "【scenario.criterion】\n给出值" in text and "【result.truthfulness】\n（未启用或未出现）" in text


# ---- 定义与加载期校验 ---------------------------------------------------------------------

def test_valid_definitions_pass():
    defs = parse(store(claims={"depends": [{"axis": "expectations", "hard": True}],
                               "materials": ["case.deliveries", "result.expectations.expectations[].statement"],
                               "output": obj(verdict=TEXT, reason=TEXT)}))
    assert check_definitions(defs, registry()) == []
    assert check_scenario(defs, ["expectations", "claims"], []) == []


@pytest.mark.parametrize("axis, needle", [
    ({"depends": [{"axis": "a2", "hard": True}], "output": obj(verdict=TEXT, reason=TEXT)}, "成环"),
    ({"materials": ["result.expectations"], "output": obj(verdict=TEXT, reason=TEXT)}, "超出读取范围"),
    ({"materials": ["case.nope"], "output": obj(verdict=TEXT, reason=TEXT)}, "不在注册表"),
    ({"depends": [{"axis": "expectations", "hard": True}], "materials": ["result.expectations.nope"],
      "output": obj(verdict=TEXT, reason=TEXT)}, "nope"),
    ({"output": obj(reason=TEXT)}, "缺 ['verdict']"),
    ({"depends": [{"axis": "expectations", "hard": False}], "trigger": {"axis": "expectations", "verdict_in": ["partial"]},
      "output": obj(verdict=TEXT, reason=TEXT)}, "只能引用硬依赖"),
    ({"depends": [{"axis": "expectations", "hard": True}], "trigger": {"axis": "expectations", "verdict_in": ["bogus"]},
      "output": obj(verdict=TEXT, reason=TEXT)}, "不在 expectations 的 verdict 枚举"),
    ({"output": obj(verdict={"type": "string", "x-fill": "program"}, reason=TEXT)}, "synth.py"),
    ({"submit": "per_item", "output": obj(verdict=TEXT, reason=TEXT)}, "items_field"),
    ({"checks": [{"covers": {"field": "reason"}}], "output": obj(verdict=TEXT, reason=TEXT)}, "缺 ['of']"),
    ({"checks": [{"covers": {"field": "reason", "of": "case.deliveries[].text"}}], "output": obj(verdict=TEXT, reason=TEXT)},
     "不在本任务的材料白名单"),
    ({"tools": ["nope"], "output": obj(verdict=TEXT, reason=TEXT)}, "未定义的公共 loop 工具"),
    ({"executor": "program", "run_mode": "isolated", "output": obj(verdict={**TEXT, "x-fill": "program"}, reason={**TEXT, "x-fill": "program"})},
     "run_mode=isolated"),
])
def test_load_time_errors(axis, needle):
    extra = {"a2": {"depends": [{"axis": "a1", "hard": True}], "output": obj(verdict=TEXT, reason=TEXT)}} if needle == "成环" else {}
    defs = parse(store(a1=axis, **extra))
    errors = check_definitions(defs, registry())
    assert any(needle in e for e in errors), errors


def test_scenario_errors_for_missing_hard_dependency_and_required_category():
    defs = parse(store(claims={"depends": [{"axis": "expectations", "hard": True}],
                               "tool_categories": [{"category": "knowledge", "required": True}],
                               "output": obj(verdict=TEXT, reason=TEXT)}))
    errors = check_scenario(defs, ["claims"], [])
    assert any("硬依赖 expectations" in e for e in errors) and any("knowledge" in e for e in errors)


def test_shared_tool_params_need_descriptions():
    defs = parse({"axes": {}, "shared_tools": {"search": {
        "description": "查知识", "params": obj(items={"type": "array"}), "output": obj(x=TEXT)}}})
    assert any("description" in e for e in check_definitions(defs, registry()))


def test_check_params_lists_known_checks():
    assert check_params("nope", {}).startswith("未知的标准校验")
    assert set(STANDARD) == {"covers", "refs_in", "quote_in_material", "quote_in_call", "searched", "from_call"}


# ---- 标准校验与验收 -----------------------------------------------------------------------

CALLS = (
    CallView("c1", "mcp_call", "knowledge", {}, 0, '{"text": "犹豫期为十五日"}', None, False),
    CallView("c2", "mcp_call", "knowledge", {}, 0, "", None, True),
    CallView("c3", "judge_blocking", "subloop", {}, 0, "{}", {"items": []}, False),
)


def make_work(**over):
    raw = {"output": obj(verdict={"type": "string", "enum": ["ok", "bad"]}, reason=TEXT,
                         items={"type": "array", "items": obj(item_id=TEXT, cites={"type": "array", "items": obj(ref=TEXT, quote=TEXT)},
                                                               searched={"type": "array", "items": TEXT})})}
    raw.update(over)
    return parse({"axes": {"t": raw}, "shared_tools": {}}).axes["t"]


def view_for(materials=None):
    return lambda stage, own: TaskView("t", own, materials or {}, calls=CALLS, stage=stage)


def test_quote_in_call_and_searched_and_from_call():
    view = TaskView("t", {}, {}, calls=CALLS)
    run = lambda name, params, scope: STANDARD[name].fn(view, scope, **params)
    assert run("quote_in_call", {"field": "c[]", "category": "knowledge"}, {"c": [{"ref": "c1", "quote": "犹豫期为 十五日"}]}) == []
    assert "没有逐字" in run("quote_in_call", {"field": "c[]"}, {"c": [{"ref": "c1", "quote": "二十日"}]})[0]
    assert "报错" in run("quote_in_call", {"field": "c[]"}, {"c": [{"ref": "c2", "quote": "x"}]})[0]
    assert "此前批次" in run("searched", {"field": "s[]", "category": "knowledge"}, {"s": ["c9"]})[0]
    assert run("searched", {"field": "s[]", "category": "knowledge"}, {"s": []})[0].startswith("s[] 至少")
    assert run("from_call", {"field": "b", "tool": "judge_blocking"}, {"b": "c3"}) == []
    assert "不是 subloop 类" in run("from_call", {"field": "b", "tool": "judge_blocking"}, {"b": "c1"})[0]


def test_covers_and_refs_in_against_materials():
    view = TaskView("t", {}, {"result.e": {"ids": ["E1", "E2"]}})
    scope = {"got": ["E1", "E1", "E3"]}
    problems = STANDARD["covers"].fn(view, scope, field="got[]", of="result.e.ids[]")
    assert any("重复" in p for p in problems) and any("漏了" in p for p in problems) and any("多了" in p for p in problems)
    assert STANDARD["refs_in"].fn(view, {"got": ["E1"]}, field="got[]", of="result.e.ids[]") == []


def test_once_submission_schema_then_checks_then_accept():
    work = make_work(output=obj(verdict={"type": "string", "enum": ["ok", "bad"]}, reason=TEXT))
    state = acceptance.Submissions()
    bad = acceptance.submit(work, state, {"verdict": "meh", "reason": "r"}, None, view_for())
    assert not bad.accepted and "verdict" in bad.reasons[0]
    good = acceptance.submit(work, state, {"verdict": "ok", "reason": "r"}, None, view_for())
    assert good.accepted and state.result == {"verdict": "ok", "reason": "r"}
    assert not acceptance.submit(work, state, {"verdict": "ok", "reason": "r"}, "x", view_for()).accepted


def test_per_item_items_are_checked_one_by_one_and_final_carries_them():
    work = make_work(submit="per_item", items_field="items",
                     checks=[{"quote_in_call": {"field": "cites[]", "category": "knowledge", "on": "item"}},
                             {"searched": {"field": "searched[]", "category": "knowledge", "on": "item"}}])
    state = acceptance.Submissions()
    rejected = acceptance.submit(work, state, {"cites": [{"ref": "c1", "quote": "三十日"}], "searched": ["c1"]}, "i1", view_for())
    assert not rejected.accepted and "没有逐字" in rejected.reasons[0]
    assert acceptance.submit(work, state, {"cites": [{"ref": "c1", "quote": "十五日"}], "searched": ["c1"]}, "i1", view_for()).accepted
    final = acceptance.submit(work, state, {"verdict": "ok", "reason": "r"}, None, view_for())
    assert final.accepted and final.result["items"][0]["item_id"] == "i1"


def test_custom_check_and_synthesis_fill_program_fields():
    output = obj(verdict={"type": "string", "enum": ["ok", "bad"], "x-fill": "program"}, reason=TEXT, n={"type": "integer"})
    work = make_work(output=output)
    work = type(work)(**{**work.__dict__, "code": Code(
        check=lambda v: [] if v.own["n"] >= 0 else ["n 不能为负"],
        synthesize=lambda v: {"verdict": "ok" if v.own["n"] else "bad"})})
    state = acceptance.Submissions()
    assert acceptance.submit(work, state, {"reason": "r", "n": -1}, None, view_for()).reasons == ("n 不能为负",)
    assert acceptance.submit(work, state, {"reason": "r", "n": 2}, None, view_for()).result["verdict"] == "ok"
    broken = type(work)(**{**work.__dict__, "code": Code(synthesize=lambda v: {"verdict": "maybe"})})
    with pytest.raises(acceptance.SynthesisError):
        acceptance.submit(broken, acceptance.Submissions(), {"reason": "r", "n": 1}, None, view_for())


def test_custom_code_is_deterministic_on_same_view():
    view = TaskView("t", {"n": 1}, {})
    check = lambda v: [f"n={v.own['n']}"]
    assert check(view) == check(view)


# ---- 元素筛选、分发、运行方式 -------------------------------------------------------------

REQ = {"sources": [{"id": "t1.user", "turn": "t1"}, {"id": "t2.user", "turn": "t2"}, {"id": "scenario.criterion", "turn": "case"}]}


def test_element_filter_selects_by_field_values_even_with_dots_in_values():
    path = paths.parse("sources[id=t1.user,scenario.criterion].turn")
    assert paths.values(REQ, path) == ["t1", "case"]
    assert paths.extract(REQ, paths.parse("sources[turn=t2]")) == [{"id": "t2.user", "turn": "t2"}]
    pruned = paths.prune(REQ, paths.parse("sources[turn=t1,case]"))
    assert [x["id"] for x in pruned["sources"]] == ["t1.user", "scenario.criterion"]
    schema = obj(sources={"type": "array", "items": obj(id=TEXT, turn=TEXT)})
    assert paths.check_schema(schema, paths.parse("sources[id=a]")) is None
    assert "筛选字段" in paths.check_schema(schema, paths.parse("sources[nope=a]"))
    with pytest.raises(ValueError):
        paths.parse("sources[id=]")


def test_material_table_code_view_keeps_structure_and_applies_filter():
    reg = Registry([Material("case.requirements", obj(sources={"type": "array", "items": obj(id=TEXT, turn=TEXT)}), "需求", lambda c, ctx: REQ)])
    table = MaterialTable(reg, {})
    entries = [parse_entry("case.requirements.sources[turn=t2]")]
    assert table.view(entries) == {"case.requirements.sources[turn=t2]": [{"id": "t2.user", "turn": "t2"}]}
    assert table.for_code(entries) == {"case.requirements": {"sources": [{"id": "t2.user", "turn": "t2"}]}}


def test_dispatch_requires_isolated_and_synth():
    defs = parse(store(a1={"output": obj(verdict=TEXT, reason=TEXT)}))
    a1 = defs.axes["a1"]
    defs.axes["a1"] = type(a1)(**{**a1.__dict__, "code": Code(dispatch=lambda v: [])})
    errors = check_definitions(defs, registry())
    assert any("dispatch.py 只用于" in e for e in errors) and any("必须有 synth.py" in e for e in errors)


def test_unknown_run_mode_is_rejected_when_parsing():
    with pytest.raises(ValueError, match="run_mode"):
        parse(store(a1={"run_mode": "bogus", "output": obj(verdict=TEXT, reason=TEXT)}))


def test_quotes_match_across_json_escaping_layers():
    from impl.core.axis_loop.text import quote_in_value
    inner = json.dumps({"subject_id": "P1", "typed_value": "平安e生保"}, ensure_ascii=False)
    seen = {"text": json.dumps({"rows": [inner]}, ensure_ascii=False)}          # JSON 里套 JSON 字符串
    assert quote_in_value('"subject_id": "P1", "typed_value": "平安e生保"', seen)
    assert quote_in_value('subject_id\\":\\"P1', seen)
    assert not quote_in_value('"subject_id": "P2"', seen)                       # 改字仍判不是原文


def test_escaped_newlines_count_as_whitespace():
    from impl.core.axis_loop.text import quote_in_text
    assert quote_in_text("第一行 第二行", "第一行\\n第二行")
    assert not quote_in_text("第一行 第三行", "第一行\\n第二行")
