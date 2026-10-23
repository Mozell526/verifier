"""AxisLoop：一个 case 一个主 loop（spec/alg/axis_loop.md §1、§5、§6、§9、§10）。

搭在 ToolLoop 上，只用它现有的 hook 事件：
- start / post_batch：台账结算 → 推送 main 轴的新任务、作废、撤下；程序任务与独立运行的轴当场跑完
- pre_tool：submit 走验收流水线；信息源工具与公共 loop 工具按门禁放行
- post_tool：给每个返回盖 call_id
- stop / ready_to_finish：所有出现过的任务都完成
三种 loop：主 loop（main 轴）、独立运行的轴的子 loop（程序启动，可按分发起多份）、公共 loop 工具的子 loop
（调用方的模型调用；只嵌一层）。预算、致命错误、上下文归档都在 Governor，三种 loop 共用一份 RunState。
"""
from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Sequence

from impl.core.tool_loop import (
    Abort, Allow, BudgetStop, Call, Continue, Deny, Done, Failed, History, Hook, LoopContext, PreDecision,
    StepClient, StopVerdict, ToolLoop)
from impl.tools.protocol import VerifiableTool, _serialize_tool_result

from . import acceptance
from .acceptance import Submissions, SynthesisError
from .checks import SUBLOOP_CATEGORY
from .definitions import RUN_ISOLATED, SUBMIT_PER_ITEM, AxisDef, Definitions, Work
from .ledger import Change, Event, Ledger
from .materials import MaterialTable, parse_entry, render
from .text import dump
from .validate import check_entry
from .view import CallView, TaskView

SUBMIT, RECALL = "submit", "recall"
AXIS_NOTE = "axis.note"

SYSTEM = """你是评测员，在一个 case 上完成一组评测任务。任务由程序陆续推送：一开始只给没有前置的任务，
某个任务被接受后，依赖它的任务才会出现。每个任务写明了说明、材料、可用工具和提交格式。

规则：
1. 按任务说明判；只依据给你的材料和工具返回，不凭自己的知识。
2. 用 submit 交：task_id 写任务名，payload 照提交格式写。分条交的任务每个分项单独交（带 item_id），全部交完再不带 item_id 交一次收尾。
3. 被拒就按原因改了再交。几个任务可以交错做，一次回复里也可以同时交多个。
4. 引用写成 {"ref": 出处, "quote": 原文}：出处是工具返回里的 call_id，或材料的标题；quote 从原文逐字摘，不改写、不拼接。
5. 同一次回复里拿到的工具返回，要到下一次回复才能引用。
6. 已经交过的任务发现交错了，可以重交来修改；依赖它的任务会被作废，需要重做。
7. 工具返回太长时会被归档，用 recall(call_id) 重看。
全部任务完成后不需要再写总结。"""

SUBLOOP_SYSTEM = """你在一个独立的上下文里完成一件任务：只看下面给你的材料和工具返回，按说明做，用 submit 交（task_id 写任务名）。
被拒就按原因改了再交。引用写成 {"ref": call_id, "quote": 原文}，quote 逐字摘自那次返回；同一次回复里拿到的返回要到下一次回复才能引用。
工具返回太长时会被归档，用 recall(call_id) 重看。交完不需要再写总结。"""


class Sources(Protocol):
    """信息源：工具（固定在工具列表里）+ 每次调用属于哪个类别、哪条登记。"""

    tools: Sequence[VerifiableTool]

    def route(self, call: Call) -> tuple[str, str]:
        """(类别, 登记)；不是信息源调用为 ("", "")。"""

    def instances(self, category: str) -> list[str]:
        """场景选用的这个类别的登记。"""

    def describe(self, category: str, instances: Sequence[str]) -> str:
        """推送给模型的说明：这些信息源有哪些工具、怎么读。"""


@dataclass
class Settings:
    llm_calls: int
    tool_calls: int
    seconds: float
    context_limit_tokens: int = 200_000
    archive_ratio: float = 0.8
    chars_per_token: float = 2.0
    max_blocked: int = 8


@dataclass
class RunState:
    """主 loop 与各子 loop 共用：全局用量与致命错误。"""

    settings: Settings
    started: float = field(default_factory=time.monotonic)
    llm_calls: int = 0
    tool_calls: int = 0
    fatal: str = ""
    archived: int = 0


class IsolatedFailed(RuntimeError):
    """独立运行的轴没跑成：整个 case 记运行失败。"""


class Governor(BudgetStop):
    """全局预算 + 致命错误 + 上下文归档。每个 loop 一个实例，共用 RunState。"""

    def __init__(self, run: RunState) -> None:
        super().__init__()
        self.run = run

    def _limits(self) -> Optional[str]:
        s = self.run.settings
        if self.run.fatal:
            return self.run.fatal
        if self.run.llm_calls >= s.llm_calls:
            return f"budget: llm_calls 已达全局上限 {s.llm_calls}"
        if time.monotonic() - self.run.started > s.seconds:
            return f"budget: 已超过全局墙钟上限 {s.seconds:g}s"
        return None

    def before_step(self, history: History) -> PreDecision:
        if why := self._limits():
            return Abort(why)
        if why := self._fit_context(history):
            self.run.fatal = why
            return Abort(why)
        self.run.llm_calls += 1
        return Allow()

    def step_note(self, history: History) -> str:
        return ""

    def pre_tool(self, history: History, call: Call) -> PreDecision:
        if self.run.fatal:
            return Abort(self.run.fatal)
        if self.run.tool_calls >= self.run.settings.tool_calls:
            return Abort(f"budget: tool_calls 已达全局上限 {self.run.settings.tool_calls}")
        self.run.tool_calls += 1
        return Allow()

    def _tokens(self, history: History) -> float:
        return sum(len(str(m.get("content") or "")) for m in history.messages) / self.run.settings.chars_per_token

    def _fit_context(self, history: History) -> str:
        """接近上限就把较早的工具返回换成归档提示（原文仍在调用记录里，recall 可重看）；仍超限 → 失败原因。"""
        s = self.run.settings
        if self._tokens(history) <= s.context_limit_tokens * s.archive_ratio:
            return ""
        last_batch = max((c.batch for c in history.calls), default=-1)
        recent = {c.id for c in history.calls if c.batch == last_batch}
        for message in history.messages:
            if self._tokens(history) <= s.context_limit_tokens * s.archive_ratio:
                break
            content = message.get("content")
            if message.get("role") != "tool" or not isinstance(content, str) or content.startswith("[已归档]"):
                continue
            try:
                ref = str(json.loads(content).get("call_id", ""))
            except (ValueError, AttributeError):
                ref = ""
            if not ref or any(ref.endswith(f"c{i}") for i in recent):
                continue
            message["content"] = f"[已归档] call_id={ref}，需要时用 recall(call_id) 重看"
            self.run.archived += 1
        if self._tokens(history) > s.context_limit_tokens:
            return f"上下文超限：归档后仍约 {int(self._tokens(history))} tokens，上限 {s.context_limit_tokens}"
        return ""


def _is_error(result: Any) -> bool:
    return isinstance(result, Mapping) and bool(result.get("isError") or result.get("error") or result.get("status") == "failed")


def submit_tool(names: Sequence[str]) -> VerifiableTool:
    return VerifiableTool(
        tool_id=SUBMIT, execute_fn=lambda **_: {"accepted": True},
        description="交一个任务的结果。合规返回 accepted=true；不合规会被拒并给出原因，改了再交。",
        parameters={"type": "object", "properties": {
            "task_id": {"type": "string", "enum": list(names), "description": "任务名"},
            "item_id": {"type": "string", "description": "分条交的任务：分项编号；交收尾时不填"},
            "payload": {"type": "object", "description": "按该任务的提交格式写的内容"}},
            "required": ["task_id", "payload"]})


def _format(work: Work) -> str:
    if work.submit == SUBMIT_PER_ITEM:
        return (f"分条交：每个分项 submit(task_id={work.id!r}, item_id=<分项编号，写进 {work.item_key}>, payload=分项)，"
                f"分项格式：{dump(acceptance.item_payload_schema(work))}\n"
                f"全部分项交完后 submit(task_id={work.id!r}, payload=收尾)，收尾格式：{dump(work.model_schema())}")
    return f"一次交齐：submit(task_id={work.id!r}, payload=...)，格式：{dump(work.model_schema())}"


class _Base(Hook):
    """三种 loop 共用：盖 call_id、组视图、recall、信息源与公共 loop 工具的门禁。"""

    def __init__(self, loop: "AxisLoop", prefix: str, shared: Sequence[str]) -> None:
        self.loop = loop
        self.sources = loop.sources
        self.prefix = prefix
        self.shared = set(shared)
        self.history: Optional[History] = None

    def call_id(self, call: Call) -> str:
        return f"{self.prefix}c{call.id}"

    def post_tool(self, history: History, call: Call) -> Any:
        if call.tool == SUBMIT or not isinstance(call.result, Mapping):
            return call.result
        return {**call.result, "call_id": self.call_id(call)}

    def post_batch(self, history: History, calls: Sequence[Call]) -> Sequence[str]:
        for call in calls:
            if call.tool in self.shared and isinstance(call.result, Mapping) and call.result.get("status") == "failed":
                self.loop.run_state.fatal = self.loop.run_state.fatal or f"公共 loop 工具 {call.tool} 失败：{call.result.get('reason')}"
        return ()

    def category(self, call: Call) -> str:
        return SUBLOOP_CATEGORY if call.tool in self.shared else self.sources.route(call)[0]

    def call_views(self, history: History) -> list[CallView]:
        out = []
        for call in history.calls:
            if call.tool in (SUBMIT, RECALL) or call.denied:
                continue
            result = call.result
            structured = result.get("structuredContent") if isinstance(result, Mapping) else None
            if call.tool in self.shared and isinstance(result, Mapping):
                structured = result.get("result")
            out.append(CallView(self.call_id(call), call.tool, self.category(call), dict(call.args), call.batch,
                                str(_serialize_tool_result(result) or ""), structured, not call.ok or _is_error(result)))
        return out

    def view(self, history: History, entries: Sequence[str], own: Mapping[str, Any], stage: str, axis_id: str,
             params: Mapping[str, Any] | None = None, parts: Sequence[Mapping[str, Any]] = ()) -> TaskView:
        materials = self.loop.table.for_code([parse_entry(t) for t in entries], axis_id)
        return TaskView(axis_id, own, materials, dict(params or {}), self.call_views(history), stage, tuple(parts))

    def recall_tool(self) -> VerifiableTool:
        def recall(call_id: str) -> Any:
            history = self.history or History()
            call = next((c for c in history.calls if self.call_id(c) == call_id), None)
            if call is None:
                return {"isError": True, "error": f"没有 call_id={call_id} 的调用"}
            return {"recalled": call_id, "result": call.result}
        return VerifiableTool(tool_id=RECALL, execute_fn=recall, description="重看一次已归档的工具返回原文。",
                              parameters={"type": "object", "properties": {
                                  "call_id": {"type": "string", "description": "要重看的 call_id"}}, "required": ["call_id"]})

    def gate_tool(self, call: Call, instances: Mapping[str, set[str]], shared: set[str]) -> PreDecision:
        if call.tool in self.shared:
            return Allow() if call.tool in shared else Deny(f"{call.tool} 现在不能用：还没有出现选用它的任务")
        category, instance = self.sources.route(call)
        if category and instance not in instances.get(category, set()):
            return Deny(f"{instance or category} 现在不能用：这个任务没有选用它")
        return Allow()


class _Submitter(_Base):
    """只做一份工作的子 loop（独立运行的轴的一份、公共 loop 工具的一次调用）：收尾被接受即完成。"""

    def __init__(self, loop: "AxisLoop", work: Work, axis_id: str, entries: Sequence[str], prefix: str,
                 shared: Sequence[str], users: Sequence[str], params: Mapping[str, Any] | None = None) -> None:
        super().__init__(loop, prefix, shared)
        self.work, self.axis_id, self.entries, self.params = work, axis_id, list(entries), dict(params or {})
        self.state = Submissions()
        self.instances = {c.category: {i for k in users for i in loop.allowed_instances(k, c.category)}
                          for c in work.tool_categories}

    def start(self, history: History, ctx: LoopContext) -> Sequence[str]:
        self.history = history
        return ()

    def pre_tool(self, history: History, call: Call) -> PreDecision:
        self.history = history
        if call.tool != SUBMIT:
            return self.gate_tool(call, self.instances, self.shared)
        if call.args.get("task_id") != self.work.id:
            return Deny(f"task_id 只能是 {self.work.id}")
        make_view = lambda stage, own: self.view(history, self.entries, own, stage, self.axis_id, self.params)
        try:
            outcome = acceptance.submit(self.work, self.state, call.args.get("payload"), call.args.get("item_id") or None, make_view)
        except SynthesisError as exc:
            self.loop.run_state.fatal = str(exc)
            return Abort(str(exc))
        if not outcome.accepted:
            return Deny("submit 被拒：" + "；".join(outcome.reasons))
        return Allow()

    def ready_to_finish(self, history: History) -> bool:
        return self.state.result is not None or bool(self.loop.run_state.fatal)

    def stop(self, history: History, blocked: int) -> StopVerdict:
        if self.loop.run_state.fatal:
            return Failed(self.loop.run_state.fatal)
        return Done() if self.state.result is not None else Continue(f"还没有被接受的提交；用 submit(task_id={self.work.id!r}) 交。")


def _task_text(loop: "AxisLoop", work: Work, axis_id: str, entries: Sequence[str], title: str, shared: Sequence[str],
               users: Sequence[str], params: Mapping[str, Any] | None = None) -> str:
    parts = [title, "说明：" + work.instruction]
    chosen = [parse_entry(t) for t in entries]
    if axis_id and loop.table.registry.get(AXIS_NOTE) and AXIS_NOTE not in entries:
        chosen.insert(0, parse_entry(AXIS_NOTE))
    values = loop.table.view(chosen, axis_id)
    if values:
        parts.append("材料：\n" + render(values))
    if params:
        parts.append("调用参数：\n" + dump(params))
    tools = []
    for cat in work.tool_categories:
        instances = sorted({i for k in users for i in loop.allowed_instances(k, cat.category)})
        if instances:
            tools.append(loop.sources.describe(cat.category, instances))
    for name in shared:
        tools.append(f"工具 {name}：{loop.defs.shared_tools[name].description}")
    if tools:
        parts.append("可用工具：\n" + "\n".join(tools))
    parts.append("提交：" + _format(work))
    return "\n".join(parts)


class _SharedTool:
    """公共 loop 工具 = 一个工具：每次调用新开一个 ToolLoop（各自的提交状态），材料按它的白名单、加上参数。"""

    def __init__(self, loop: "AxisLoop", name: str) -> None:
        self.loop, self.name, self.tool_def = loop, name, loop.defs.shared_tools[name]

    def tool(self) -> VerifiableTool:
        params = dict(self.tool_def.params) or {"type": "object", "properties": {}, "required": []}
        return VerifiableTool(tool_id=self.name, description=self.tool_def.description, parameters=params, execute_fn=self.execute)

    def execute(self, **params: Any) -> Any:
        problems = acceptance.schema_errors(self.tool_def.params, params) if self.tool_def.params else []
        if problems:
            return {"status": "error", "isError": True, "error": "参数不对：" + "；".join(problems)}
        work, users = self.tool_def, self.loop.users_of(self.name)
        gate = _Submitter(self.loop, work, "", work.materials, f"{self.name}#{self.loop.run_state.tool_calls}.", (), users, params)
        text = _task_text(self.loop, work, "", work.materials, f"【任务 {work.id}】", (), users, params)
        tools = [submit_tool([work.id]), gate.recall_tool(), *(self.loop.sources.tools if work.tool_categories else [])]
        child = ToolLoop(self.name, SUBLOOP_SYSTEM, tools, self.loop.client, completion_hook=gate,
                         hooks={"start": [gate], "pre_tool": [gate], "post_tool": [gate]},
                         end=lambda history: {"result": gate.state.result}, budget=Governor(self.loop.run_state),
                         max_blocked=self.loop.run_state.settings.max_blocked)
        # 嵌在调用方那一步里跑：as_tool 让它继承调用方的 trace_id 与 stage。
        value = child.as_tool(work.description, self.tool().parameters, render=lambda args: text).execute_fn(**params)
        failed = isinstance(value, Mapping) and value.get("status") == "failed"
        self.loop.ledger.events.append(Event(self.loop.batch, "shared_tool", self.name,
                                             reasons=(f"failed: {value.get('reason')}",) if failed else ("complete",)))
        return {**value, "isError": True} if failed else value


@dataclass
class LoopReport:
    status: str
    reason: str
    results: Mapping[str, Optional[Mapping[str, Any]]]
    states: Mapping[str, str]
    events: list[Event]
    llm_calls: int
    tool_calls: int
    seconds: float
    archived: int
    messages: list[dict]


class AxisLoop:
    def __init__(self, defs: Definitions, enabled: Sequence[str], table: MaterialTable, sources: Sources,
                 client: StepClient, settings: Settings, *, axis_sources: Mapping[str, Sequence[str]] | None = None) -> None:
        """axis_sources：场景里各轴挑的信息源登记（不挑 = 该类别下场景选用的全部）。"""
        self.defs = defs
        self.table = table
        self.sources = sources
        self.client = client
        self.run_state = RunState(settings)
        self.axis_sources = {k: list(v) for k, v in (axis_sources or {}).items()}
        self.enabled = list(enabled)
        self.ledger = Ledger(defs, enabled, table.results, self._run_auto)
        self.main_shared = sorted({t for k in self.enabled if not defs.axes[k].automatic for t in defs.axes[k].tools})
        self.shared_impl = {name: _SharedTool(self, name) for name in sorted({t for k in self.enabled for t in defs.axes[k].tools})}
        self.gate = _MainGate(self)
        self.ctx = LoopContext(trace_id="")
        self.batch = 0

    # ---- 选用关系 ----

    def allowed_instances(self, axis_id: str, category: str) -> list[str]:
        chosen = self.axis_sources.get(axis_id)
        return [i for i in self.sources.instances(category) if not chosen or i in chosen]

    def users_of(self, tool: str) -> list[str]:
        """选用这个公共 loop 工具的轴（信息源取它们挑的并集）。"""
        return [k for k in self.enabled if tool in self.defs.axes[k].tools]

    # ---- 程序推进的轴（程序任务、独立运行的轴） ----

    def _run_auto(self, axis: AxisDef, state: Submissions) -> None:
        if axis.run_mode == RUN_ISOLATED:
            self._run_isolated(axis, state)
            return
        view = self.gate.view(self.gate.history or History(), axis.materials, {}, acceptance.STAGE_FINAL, axis.id)
        state.result = self._synthesize(axis, view)

    def _synthesize(self, axis: AxisDef, view: TaskView) -> dict[str, Any]:
        try:
            filled = axis.code.synthesize(view)
        except Exception as exc:
            raise SynthesisError(f"{axis.id}: synth.py 出错：{type(exc).__name__}: {exc}") from exc
        problems = acceptance.schema_errors(axis.output, filled)
        if problems:
            raise SynthesisError(f"{axis.id}: 合成结果不合输出 schema：" + "；".join(problems[:5]))
        return dict(filled)

    def _run_isolated(self, axis: AxisDef, state: Submissions) -> None:
        if not axis.code.dispatch:
            state.result = self._run_child(axis, axis, axis.materials, axis.id)
            return
        base = self.gate.view(self.gate.history or History(), axis.materials, {}, acceptance.STAGE_FINAL, axis.id)
        try:
            plan = axis.code.dispatch(base)
        except Exception as exc:
            raise SynthesisError(f"{axis.id}: dispatch.py 出错：{type(exc).__name__}: {exc}") from exc
        if not isinstance(plan, list) or not plan:
            raise SynthesisError(f"{axis.id}: dispatch.py 必须返回非空列表 [{{id, materials}}]")
        allowed = {parse_entry(t).name for t in axis.materials}
        part_work = acceptance.part_work(axis)
        parts = []
        for spec in plan:
            pid, entries = (spec or {}).get("id"), (spec or {}).get("materials")
            if not isinstance(pid, str) or not pid or not isinstance(entries, list) or not entries:
                raise SynthesisError(f"{axis.id}: dispatch.py 每份要有非空 id 与 materials 列表，得到 {spec!r}")
            for text in entries:
                problem = check_entry(text, axis, self.defs, self.table.registry)
                if not problem and parse_entry(text).name not in allowed:
                    problem = f"{text} 不在这个轴的材料白名单里"
                if problem:
                    raise SynthesisError(f"{axis.id}: dispatch.py 给 {pid} 的选择不合法：{problem}")
            parts.append({"id": pid, "result": self._run_child(axis, part_work, entries, f"{axis.id}[{pid}]")})
        view = self.gate.view(self.gate.history or History(), axis.materials, {}, acceptance.STAGE_FINAL, axis.id, parts=parts)
        state.result = self._synthesize(axis, view)

    def _run_child(self, axis: AxisDef, work: Work, entries: Sequence[str], label: str) -> Mapping[str, Any]:
        gate = _Submitter(self, work, axis.id, entries, f"{label}.", axis.tools, [axis.id])
        text = _task_text(self, work, axis.id, entries, f"【任务 {work.id}：{axis.title}】", axis.tools, [axis.id])
        tools = [submit_tool([work.id]), gate.recall_tool(), *(self.sources.tools if work.tool_categories else []),
                 *(self.shared_impl[t].tool() for t in axis.tools)]
        child = ToolLoop(label.replace("[", "_").replace("]", ""), SUBLOOP_SYSTEM, tools, self.client, completion_hook=gate,
                         hooks={"start": [gate], "pre_tool": [gate], "post_tool": [gate], "post_batch": [gate]},
                         end=lambda history: gate.state.result, budget=Governor(self.run_state),
                         max_blocked=self.run_state.settings.max_blocked)
        stage = f"{self.ctx.stage}/{label}" if self.ctx.stage else label
        result = child.run(text, LoopContext(trace_id=self.ctx.trace_id, stage=stage))
        self.ledger.events.append(Event(self.batch, "subloop", label,
                                        reasons=(result.status if not result.reason else f"{result.status}: {result.reason}",)))
        if result.status != "complete" or gate.state.result is None:
            raise IsolatedFailed(f"独立运行的轴 {label} 没跑成：{result.reason or self.run_state.fatal}")
        return gate.state.result

    # ---- 推送（只推 main 轴） ----

    def push(self, change: Change) -> list[str]:
        def text(key: str, title: str) -> str:
            axis = self.defs.axes[key]
            return _task_text(self, axis, key, axis.materials, title, axis.tools, [key])
        notes = [text(k, f"【任务 {k}：{self.defs.axes[k].title}】") for k in change.appeared]
        notes += [text(k, f"【重做 {k}：{self.defs.axes[k].title}】") + "\n（上游被修改，之前交的作废，按新材料重交）"
                  for k in change.invalidated]
        notes += [f"【撤下 {k}】触发条件不再满足，这个任务不用做了，之前交的作废。" for k in change.withdrawn
                  if not self.defs.axes[k].automatic]
        return notes

    def main_permissions(self) -> tuple[dict[str, set[str]], set[str]]:
        """主 loop 当前放行的信息源登记与公共 loop 工具（已出现的 main 轴带进来的，放行后不收回）。"""
        instances: dict[str, set[str]] = {}
        shared: set[str] = set()
        for key in self.enabled:
            axis = self.defs.axes[key]
            if axis.automatic or self.ledger.state[key] not in ("open", "done"):
                continue
            for cat in axis.tool_categories:
                instances.setdefault(cat.category, set()).update(self.allowed_instances(key, cat.category))
            shared.update(axis.tools)
        return instances, shared

    # ---- 运行 ----

    def run(self, case_header: str, ctx: LoopContext) -> LoopReport:
        self.ctx = ctx
        visible = [k for k in self.enabled if not self.defs.axes[k].automatic]
        tools = [submit_tool(visible or ["-"]), self.gate.recall_tool(), *self.sources.tools,
                 *(self.shared_impl[t].tool() for t in self.main_shared)]
        loop = ToolLoop("axis_loop", SYSTEM, tools, self.client, completion_hook=self.gate,
                        hooks={"start": [self.gate], "pre_tool": [self.gate], "post_tool": [self.gate],
                               "post_batch": [self.gate]},
                        end=lambda history: None, budget=Governor(self.run_state),
                        max_blocked=self.run_state.settings.max_blocked)
        result = loop.run(case_header, ctx)
        status = "complete" if result.status == "complete" and not self.run_state.fatal else "failed"
        return LoopReport(status=status, reason=self.run_state.fatal or result.reason,
                          results={k: self.table.results.get(k) for k in self.enabled},
                          states=dict(self.ledger.state), events=list(self.ledger.events),
                          llm_calls=self.run_state.llm_calls, tool_calls=self.run_state.tool_calls,
                          seconds=round(time.monotonic() - self.run_state.started, 1),
                          archived=self.run_state.archived, messages=result.messages)


class _MainGate(_Base):
    def __init__(self, loop: AxisLoop) -> None:
        super().__init__(loop, "", loop.main_shared)
        self.accepted: list[tuple[str, Mapping[str, Any]]] = []  # 本批被接受的收尾 (任务, 结果)

    def start(self, history: History, ctx: LoopContext) -> Sequence[str]:
        self.history = history
        return self._settle([])

    def _settle(self, changed: Sequence[str]) -> list[str]:
        try:
            change = self.loop.ledger.settle(changed, self.loop.batch)
        except (SynthesisError, IsolatedFailed) as exc:
            self.loop.run_state.fatal = self.loop.run_state.fatal or str(exc)
            return []
        return self.loop.push(change)

    def pre_tool(self, history: History, call: Call) -> PreDecision:
        self.history = history
        if call.tool == SUBMIT:
            return self._submit(history, call)
        instances, shared = self.loop.main_permissions()
        return self.gate_tool(call, instances, shared)

    def _submit(self, history: History, call: Call) -> PreDecision:
        key, item_id, payload = call.args.get("task_id"), call.args.get("item_id"), call.args.get("payload")
        ledger = self.loop.ledger
        if key not in ledger.state or not ledger.visible(key):
            self._event("reject", str(key), call, ("任务未出现或不可提交",))
            return Deny(f"任务 {key} 现在不能交：它还没出现，或不是需要你交的任务。当前待交：{ledger.open_tasks()}")
        axis = self.loop.defs.axes[key]
        make_view = lambda stage, own: self.view(history, axis.materials, own, stage, key)
        try:
            outcome = acceptance.submit(axis, ledger.subs[key], payload, item_id or None, make_view)
        except SynthesisError as exc:
            self.loop.run_state.fatal = str(exc)
            return Abort(str(exc))
        if not outcome.accepted:
            self._event("reject", key, call, outcome.reasons, item_id)
            return Deny(f"submit（{key}{'/' + item_id if item_id else ''}）被拒：" + "；".join(outcome.reasons))
        self._event("accept", key, call, (), item_id)
        if outcome.result is not None:
            self.accepted.append((key, outcome.result))
        return Allow()

    def _event(self, kind: str, key: str, call: Call, reasons: Sequence[str], item_id: str = "") -> None:
        self.loop.ledger.events.append(Event(self.loop.batch, kind, key, item_id or "", self.call_id(call), tuple(reasons)))

    def post_batch(self, history: History, calls: Sequence[Call]) -> Sequence[str]:
        super().post_batch(history, calls)
        changed = [key for key, result in self.accepted if self.loop.ledger.accept(key, result)]
        self.accepted = []
        self.loop.batch += 1
        return self._settle(changed)

    def ready_to_finish(self, history: History) -> bool:
        return self.loop.ledger.finished() or bool(self.loop.run_state.fatal)

    def stop(self, history: History, blocked: int) -> StopVerdict:
        if self.loop.run_state.fatal:
            return Failed(self.loop.run_state.fatal)
        if self.loop.ledger.finished():
            return Done()
        return Continue(f"还有任务没完成：{self.loop.ledger.open_tasks()}。继续做并用 submit 提交。")
