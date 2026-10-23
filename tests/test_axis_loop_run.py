"""AxisLoop 运行（spec/alg/axis_loop.md §5、§6；实施 P4、R1–R3）。

模型用脚本代替：按 stage 分路（主 loop、各独立运行的轴、公共 loop 工具），每路一串回复。
子 loop 的 call_id 前缀运行时才定，脚本里需要引用时由 `fill_refs` 从那一路刚看到的工具返回里取。
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict, deque

from impl.core.axis_loop.definitions import Code, parse
from impl.core.axis_loop.loop import AxisLoop, Governor, RunState, Settings
from impl.core.axis_loop.materials import Material, MaterialTable, Registry
from impl.core.tool_loop import Call, History, LoopContext, Step
from impl.tools.protocol import VerifiableTool

DELIVERY = "您的保单现金价值为 12345 元。"
T1_TEXT = "这张保单现在退保能拿多少？"
T2_TEXT = "不对，我问的是另一张保单"
EVIDENCE = "保单 P1 现金价值 12345 元"
TEXT = {"type": "string"}
STRS = {"type": "array", "items": TEXT}
CITE = {"type": "array", "items": {"type": "object", "properties": {"ref": TEXT, "quote": TEXT}, "required": ["ref", "quote"]}}
REF = "<上一次工具返回的 call_id>"


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props)}


def prog(schema):
    return {**schema, "x-fill": "program"}


REQUIREMENTS = {"sources": [
    {"id": "t1.user", "turn": "t1", "component": "user", "value": T1_TEXT},
    {"id": "t2.user", "turn": "t2", "component": "user", "value": T2_TEXT},
]}


def registry():
    return Registry([
        Material("case.requirements", obj(sources={"type": "array", "items": obj(id=TEXT, turn=TEXT, component=TEXT, value=TEXT)}),
                 "需求侧材料", lambda case, ctx: REQUIREMENTS),
        Material("case.deliveries", {"type": "array", "items": obj(turn=TEXT, text=TEXT)}, "回答",
                 lambda case, ctx: [{"turn": "t1", "text": DELIVERY}]),
        Material("axis.note", TEXT, "场景对轴的描述", lambda case, ctx: f"（{ctx['axis']} 的场景描述）"),
    ])


def per_turn(view):
    turns = sorted({s["turn"] for s in view.materials["case.requirements"]["sources"]})
    return [{"id": t, "materials": [f"case.requirements.sources[turn={t}]"]} for t in turns]


def merge_turns(view):
    items = [{**e, "expectation_id": f"{p['id']}.{e['expectation_id']}"} for p in view.parts for e in p["result"]["expectations"]]
    return {"verdict": "complete", "reason": "合并", "expectations": items}


def main_synth(view):
    f, c = view.materials["result.fulfillment"], view.materials["result.carry"]
    verdict = "done" if f["verdict"] == "fulfilled" else ("cannot" if c and c["verdict"] == "cannot" else "not_done")
    return {"verdict": verdict, "reason": "合成"}


def definitions(*, synth_main=None, dispatch=per_turn, truth_checks=True):
    v = lambda *values: {"type": "string", "enum": list(values)}
    expectation = obj(expectation_id=TEXT, statement=TEXT)
    store = {"axes": {
        "expectations": {"title": "需求", "run_mode": "isolated", "role": "analysis", "instruction": "写这一轮的期望",
                         "materials": ["case.requirements"],
                         "output": obj(verdict=prog(v("complete")), reason=TEXT, expectations={"type": "array", "items": expectation})},
        "blocking": {"title": "blocking", "run_mode": "isolated", "instruction": "判每条期望是不是 blocking",
                     "depends": [{"axis": "expectations", "hard": True}],
                     "materials": ["result.expectations.expectations[].{expectation_id, statement}"],
                     "output": obj(verdict=v("ok"), reason=TEXT, items={"type": "array", "items": obj(expectation_id=TEXT, blocking={"type": "boolean"})}),
                     "checks": [{"covers": {"field": "items[].expectation_id", "of": "result.expectations.expectations[].expectation_id"}}]},
        "claims": {"title": "说法", "instruction": "抽说法", "role": "analysis", "depends": [{"axis": "expectations", "hard": True}],
                   "materials": ["case.deliveries"],
                   "output": obj(verdict=v("some", "none"), reason=TEXT, spans=STRS),
                   "checks": [{"quote_in_material": {"field": "spans[]", "material": "case.deliveries"}}]},
        "truth": {"title": "真实性", "run_mode": "isolated", "instruction": "先调 search 取证再判", "tools": ["search"],
                  "depends": [{"axis": "claims", "hard": True}], "materials": ["result.claims"],
                  "output": obj(verdict=v("verified", "refuted"), reason=TEXT, basis=CITE),
                  "checks": [{"quote_in_call": {"field": "basis[]", "category": "subloop"}}] if truth_checks else []},
        "fulfillment": {"title": "兑现", "instruction": "判给到没有",
                        "depends": [{"axis": "expectations", "hard": True}, {"axis": "blocking", "hard": True},
                                    {"axis": "truth", "hard": False}],
                        "materials": ["case.deliveries", "result.expectations", "result.blocking", "result.truth"],
                        "output": obj(verdict=v("fulfilled", "not_fulfilled"), reason=TEXT)},
        "carry": {"title": "承载性", "instruction": "判做不做得了", "depends": [{"axis": "fulfillment", "hard": True}],
                  "trigger": {"axis": "fulfillment", "verdict_in": ["not_fulfilled"]},
                  "tool_categories": [{"category": "knowledge", "required": False}],
                  "output": obj(verdict=v("cannot", "wrong"), reason=TEXT)},
        "main": {"title": "主轴", "executor": "program", "depends": [{"axis": "fulfillment", "hard": True}, {"axis": "carry", "hard": False}],
                 "materials": ["result.fulfillment", "result.carry"],
                 "output": obj(verdict=prog(v("done", "not_done", "cannot")), reason=prog(TEXT))},
    }, "shared_tools": {
        "search": {"description": "查知识源", "instruction": "按清单取证", "params": obj(items={**STRS, "description": "待查项"}),
                   "tool_categories": [{"category": "knowledge", "required": True}],
                   "output": obj(found=CITE), "checks": [{"quote_in_call": {"field": "found[]", "category": "knowledge"}}]},
    }}
    defs = parse(store)
    axes = dict(defs.axes)
    axes["expectations"] = type(axes["expectations"])(**{**axes["expectations"].__dict__,
                                                         "code": Code(dispatch=dispatch, synthesize=merge_turns)})
    axes["main"] = type(axes["main"])(**{**axes["main"].__dict__, "code": Code(synthesize=synth_main or main_synth)})
    return type(defs)(axes=axes, shared_tools=defs.shared_tools)


class FakeSources:
    def __init__(self):
        self.tools = [VerifiableTool(tool_id="kb_search", description="查知识源", execute_fn=lambda source, query: {"text": EVIDENCE},
                                     parameters={"type": "object", "properties": {
                                         "source": {"type": "string", "description": "登记"},
                                         "query": {"type": "string", "description": "查询"}}, "required": ["source", "query"]})]

    def route(self, call):
        return ("knowledge", call.args.get("source", "")) if call.tool == "kb_search" else ("", "")

    def instances(self, category):
        return ["kb"] if category == "knowledge" else []

    def describe(self, category, instances):
        return f"{category}: {instances}，用 kb_search(source, query)"


_ids = itertools.count()


def call(name, **args):
    return {"id": f"t{next(_ids)}", "type": "function", "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


def submit(task, payload, item_id=None):
    args = {"task_id": task, "payload": payload}
    if item_id:
        args["item_id"] = item_id
    return call("submit", **args)


def fill_refs(reply, messages):
    """把回复里的占位 REF 换成这一路最近一次工具返回的 call_id。"""
    refs = [json.loads(m["content"]).get("call_id") for m in messages if m.get("role") == "tool"
            and str(m.get("content")).startswith("{") and "call_id" in str(m.get("content"))]
    return json.loads(json.dumps(reply, ensure_ascii=False).replace(REF, refs[-1] if refs else REF))


class Script:
    """按 stage 分路：路名按优先顺序匹配 stage 子串（公共 loop 工具 > 独立运行的轴 > 主 loop）。"""

    def __init__(self, routes, order):
        self.routes = {k: deque(v) for k, v in routes.items()}
        self.order = order
        self.seen = defaultdict(list)

    def complete_step(self, messages, functions, *, trace_id, stage):
        route = next((k for k in self.order if k in stage), "main")
        self.seen[route].append([dict(m) for m in messages])
        reply = self.routes[route].popleft() if self.routes.get(route) else None
        if not reply or isinstance(reply, str):
            return Step({"role": "assistant", "content": reply or "完成"})
        return Step({"role": "assistant", "content": "", "tool_calls": fill_refs(reply, messages)})

    def texts(self, route):
        return [str(m.get("content")) for request in self.seen[route] for m in request]


ORDER = ["search", "truth", "blocking", "expectations[t1]", "expectations[t2]"]
ALL = ("expectations", "blocking", "claims", "truth", "fulfillment", "carry", "main")


def run(script, defs=None, enabled=ALL, **settings):
    loop = AxisLoop(defs or definitions(), list(enabled), MaterialTable(registry(), {}), FakeSources(), script,
                    Settings(llm_calls=settings.get("llm_calls", 60), tool_calls=80, seconds=60,
                             context_limit_tokens=settings.get("context", 200_000)))
    return loop.run("case 头", LoopContext(trace_id="t", stage="axis_loop"))


CLAIMS = {"verdict": "some", "reason": "r", "spans": ["12345 元"]}


def happy_routes(fulfillment="not_fulfilled"):
    return {
        "expectations[t1]": [[submit("expectations", {"reason": "r", "expectations": [{"expectation_id": "E1", "statement": "给出现金价值"}]})]],
        "expectations[t2]": [[submit("expectations", {"reason": "r", "expectations": [{"expectation_id": "E1", "statement": "改问另一张"}]})]],
        "blocking": [[submit("blocking", {"verdict": "ok", "reason": "r", "items": [
            {"expectation_id": "t1.E1", "blocking": True}, {"expectation_id": "t2.E1", "blocking": True}]})]],
        "truth": [[call("search", items=["现金价值 12345 元"])],
                  [submit("truth", {"verdict": "verified", "reason": "原文一致", "basis": [{"ref": REF, "quote": "12345 元"}]})]],
        "search": [[call("kb_search", source="kb", query="现金价值")],
                   [submit("search", {"found": [{"ref": REF, "quote": "现金价值 12345 元"}]})]],
        "main": [[submit("claims", CLAIMS)],
                 [submit("fulfillment", {"verdict": fulfillment, "reason": "r"})],
                 [call("kb_search", source="kb", query="团险")],
                 [submit("carry", {"verdict": "cannot", "reason": "知识源里没有"})],
                 "完成"],
    }


def test_end_to_end_isolated_axes_dispatch_and_shared_tool():
    script = Script(happy_routes(), ORDER)
    report = run(script)
    assert report.status == "complete", report.reason
    assert all(state in ("done", "absent") for state in report.states.values()), report.states
    assert [e["expectation_id"] for e in report.results["expectations"]["expectations"]] == ["t1.E1", "t2.E1"]
    assert report.results["truth"]["verdict"] == "verified"
    assert report.results["main"] == {"verdict": "cannot", "reason": "合成"}
    kinds = [(e.kind, e.task_id) for e in report.events]
    assert {("subloop", "expectations[t1]"), ("subloop", "expectations[t2]"), ("isolated", "expectations"),
            ("isolated", "blocking"), ("isolated", "truth"), ("shared_tool", "search"), ("program", "main")} <= set(kinds)
    # 分发：每轮只看到自己那一轮
    assert any(T1_TEXT in t for t in script.texts("expectations[t1]")) and not any(T2_TEXT in t for t in script.texts("expectations[t1]"))
    assert any(T2_TEXT in t for t in script.texts("expectations[t2]")) and not any(T1_TEXT in t for t in script.texts("expectations[t2]"))
    # blocking 看不到交付；取证原文只在真实性子 loop 里，主 loop 看不到
    assert not any(DELIVERY in t for t in script.texts("blocking"))
    assert any(EVIDENCE in t for t in script.texts("search"))
    assert any("现金价值 12345 元" in t for t in script.texts("truth"))   # 真实性子 loop 拿到的是取证结果
    before_carry = [r for r in script.seen["main"] if not any("【任务 carry" in str(m.get("content")) for m in r)]
    assert before_carry and not any(EVIDENCE in str(m.get("content")) or "现金价值 12345 元" in str(m.get("content"))
                                    for r in before_carry for m in r)
    # 主 loop 里只推了 main 轴的任务
    pushed = " ".join(script.texts("main"))
    assert "【任务 claims" in pushed and "【任务 fulfillment" in pushed
    assert not any(f"【任务 {k}" in pushed for k in ("expectations", "blocking", "truth"))


def test_isolated_axis_failure_fails_the_case():
    routes = happy_routes()
    routes["blocking"] = [[submit("blocking", {"verdict": "ok", "reason": "r", "items": []})]] * 30  # 一直交不过覆盖校验
    report = run(Script(routes, ORDER), llm_calls=20)
    assert report.status == "failed"


def test_dispatch_selection_outside_whitelist_fails_the_case():
    defs = definitions(dispatch=lambda view: [{"id": "t1", "materials": ["case.deliveries"]}])
    report = run(Script(happy_routes(), ORDER), defs=defs)
    assert report.status == "failed" and "不在这个轴的材料白名单里" in report.reason


def test_source_tools_in_main_are_gated_until_a_main_task_brings_the_category():
    routes = happy_routes()
    routes["main"] = [[call("kb_search", source="kb", query="x"), submit("claims", CLAIMS)]] + routes["main"][1:]
    report = run(Script(routes, ORDER))
    denied = [m for m in report.messages if m.get("role") == "tool" and "现在不能用" in str(m.get("content"))]
    assert denied and report.status == "complete", report.reason


def test_revising_a_main_axis_reruns_its_isolated_downstream():
    routes = happy_routes("fulfilled")
    # 同一批：交说法又改说法 → 真实性刚跑完就因上游修改作废、自动重跑
    routes["main"] = [[submit("claims", CLAIMS)],
                      [submit("claims", {**CLAIMS, "reason": "改了"})],
                      [submit("fulfillment", {"verdict": "fulfilled", "reason": "r"})], "完成"]
    routes["truth"] = [[submit("truth", {"verdict": "refuted", "reason": "r", "basis": []})]] * 2
    report = run(Script(routes, ORDER), defs=definitions(truth_checks=False))
    assert report.status == "complete", report.reason
    assert [e.task_id for e in report.events if e.kind == "subloop" and e.task_id == "truth"] == ["truth", "truth"]
    assert ("invalidate", "truth") in [(e.kind, e.task_id) for e in report.events]


def test_synthesis_error_fails_the_case():
    routes = happy_routes("fulfilled")
    routes["main"] = [[submit("claims", CLAIMS)], [submit("fulfillment", {"verdict": "fulfilled", "reason": "r"})], "完成"]
    routes["truth"] = [[submit("truth", {"verdict": "refuted", "reason": "r", "basis": []})]]
    defs = definitions(synth_main=lambda view: {"verdict": "bogus", "reason": "x"}, truth_checks=False)
    report = run(Script(routes, ORDER), defs=defs)
    assert report.status == "failed" and "不合输出 schema" in report.reason


def test_rejection_reasons_are_returned_to_the_model():
    routes = happy_routes("fulfilled")
    routes["main"] = [[submit("claims", {"verdict": "some", "reason": "r", "spans": ["编造的原文"]})], [submit("claims", CLAIMS)],
                      [submit("fulfillment", {"verdict": "fulfilled", "reason": "r"})], "完成"]
    routes["truth"] = [[submit("truth", {"verdict": "refuted", "reason": "r", "basis": []})]]
    report = run(Script(routes, ORDER), defs=definitions(truth_checks=False))
    rejected = [m for m in report.messages if m.get("role") == "tool" and "被拒" in str(m.get("content"))]
    assert rejected and "没有逐字出现" in rejected[0]["content"] and report.status == "complete"


def test_context_still_over_limit_after_archiving_fails_with_reason():
    defs = definitions()
    claims = defs.axes["claims"]
    only = type(defs)(axes={"claims": type(claims)(**{**claims.__dict__, "depends": ()})}, shared_tools=defs.shared_tools)
    report = run(Script({"main": ["停"]}, ORDER), defs=only, enabled=("claims",), context=10)
    assert report.status == "failed" and "上下文超限" in report.reason


def test_governor_archives_old_tool_returns_but_keeps_last_batch():
    big = json.dumps({"text": "x" * 400, "call_id": "c0"})
    history = History(messages=[{"role": "system", "content": "s"},
                                {"role": "tool", "tool_call_id": "a", "content": big},
                                {"role": "tool", "tool_call_id": "b", "content": json.dumps({"text": "y" * 400, "call_id": "c1"})}],
                      calls=[Call(0, "kb_search", {}, 0), Call(1, "kb_search", {}, 1)])
    run_state = RunState(Settings(llm_calls=5, tool_calls=5, seconds=60, context_limit_tokens=400, archive_ratio=0.5))
    assert Governor(run_state)._fit_context(history) == ""
    assert history.messages[1]["content"].startswith("[已归档] call_id=c0")
    assert history.messages[2]["content"].startswith('{"text"')
    assert run_state.archived == 1
