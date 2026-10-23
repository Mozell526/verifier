"""台账：谁出现、谁作废、谁撤下，程序任务何时合成（spec/alg/axis_loop.md §5.4）。

状态：
- hidden     还没出现（依赖没齐，或触发还判不了）
- open       已出现，等模型提交（含被作废后待重交）
- done       已完成，结果在材料表 result.<id>
- absent     不出现：触发条件判为不满足；对下游算已完成、结果为空

程序任务与独立运行的轴（axis.automatic）不进 open：依赖满足就由 run_auto 当场跑完（合成 / 起子 loop）。

全部由程序算：每批结束后 `settle(changed)` 一次，返回要推送给模型的变化与事件。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from .acceptance import Submissions, SynthesisError
from .definitions import EXECUTOR_PROGRAM, AxisDef, Definitions

HIDDEN, OPEN, DONE, ABSENT = "hidden", "open", "done", "absent"


@dataclass(frozen=True)
class Event:
    batch: int
    kind: str          # appear | invalidate | withdraw | absent | program | accept | reject | submit | subloop | archive
    task_id: str
    item_id: str = ""
    call_id: str = ""
    reasons: tuple[str, ...] = ()


@dataclass
class Change:
    appeared: list[str] = field(default_factory=list)
    invalidated: list[str] = field(default_factory=list)
    withdrawn: list[str] = field(default_factory=list)


class Ledger:
    def __init__(self, defs: Definitions, enabled: Sequence[str], results: dict[str, Optional[Mapping[str, Any]]],
                 run_auto: Callable[[AxisDef, Submissions], None]) -> None:
        """results 是材料表的 result.* 字典（共享同一个对象）；run_auto 跑程序任务 / 独立运行的轴并写 state.result。"""
        self.defs = defs
        self.enabled = [a for a in enabled]
        self.on = set(enabled)
        self.results = results
        self.run_auto = run_auto
        self.state: dict[str, str] = {a: HIDDEN for a in self.enabled}
        self.subs: dict[str, Submissions] = {a: Submissions() for a in self.enabled}
        self.events: list[Event] = []
        for axis in self.enabled:
            results[axis] = None

    # ---- 查询 ----

    def axis(self, key: str) -> AxisDef:
        return self.defs.axes[key]

    def open_tasks(self) -> list[str]:
        return [a for a in self.enabled if self.state[a] == OPEN]

    def visible(self, key: str) -> bool:
        """模型能不能交这个任务：已出现或已完成（交给已完成的就是修改）。"""
        return self.state.get(key) in (OPEN, DONE) and not self.axis(key).automatic

    def finished(self) -> bool:
        return all(self.state[a] in (DONE, ABSENT) for a in self.enabled)

    def downstream(self, key: str) -> list[str]:
        out, pending = [], [key]
        while pending:
            current = pending.pop()
            for other in self.enabled:
                if other not in out and any(d.axis == current for d in self.axis(other).depends):
                    out.append(other)
                    pending.append(other)
        return out

    # ---- 变化 ----

    def accept(self, key: str, result: Mapping[str, Any]) -> bool:
        """一个任务的收尾被接受；返回是否是修改（原来已完成）。"""
        revised = self.state[key] == DONE
        self.results[key] = result
        self.state[key] = DONE
        return revised

    def _deps_ready(self, axis: AxisDef) -> bool:
        for dep in axis.depends:
            if dep.axis in self.on:
                if self.state[dep.axis] not in (DONE, ABSENT):
                    return False
            elif dep.hard:
                return False  # 加载期已拦；这里不让它出现
        return True

    def _triggered(self, axis: AxisDef) -> Optional[bool]:
        """None = 还判不了。"""
        if axis.trigger is None:
            return True
        upstream = self.results.get(axis.trigger.axis)
        if self.state.get(axis.trigger.axis) == ABSENT:
            return False
        if upstream is None:
            return None
        return upstream.get("verdict") in axis.trigger.verdict_in

    def _clear(self, key: str) -> None:
        self.results[key] = None
        self.subs[key].reset()

    def settle(self, changed: Sequence[str], batch: int) -> Change:
        """changed：本批被修改（原来已完成、又被接受）的任务。"""
        change = Change()
        for key in changed:
            for down in self.downstream(key):
                before = self.state[down]
                if before == HIDDEN:
                    continue
                # 上游变了：下游一律退回 hidden，按新结果重新出现；已出现或已完成的（模型任务）推送作废。
                self._clear(down)
                self.state[down] = HIDDEN
                if before in (OPEN, DONE) and not self.axis(down).automatic and down not in change.invalidated:
                    change.invalidated.append(down)
                self.events.append(Event(batch, "invalidate", down, reasons=(f"{key} 被修改",)))
        progressed = True
        while progressed:
            progressed = False
            for key in self.enabled:
                axis, current = self.axis(key), self.state[key]
                if current in (OPEN, DONE) and axis.trigger and self._triggered(axis) is False:
                    self._clear(key)
                    self.state[key] = ABSENT
                    change.withdrawn.append(key)
                    self.events.append(Event(batch, "withdraw", key, reasons=("触发条件不再满足",)))
                    progressed = True
                    continue
                if current != HIDDEN or not self._deps_ready(axis):
                    continue
                triggered = self._triggered(axis)
                if triggered is None:
                    continue
                if not triggered:
                    self.state[key] = ABSENT
                    self.events.append(Event(batch, "absent", key, reasons=("触发条件未满足",)))
                elif axis.automatic:
                    self.run_auto(axis, self.subs[key])  # SynthesisError / 子 loop 失败交给调用方中止
                    self.accept(key, self.subs[key].result)
                    self.events.append(Event(batch, "program" if axis.executor == EXECUTOR_PROGRAM else "isolated", key))
                else:
                    self.state[key] = OPEN
                    if key not in change.invalidated:
                        change.appeared.append(key)
                    self.events.append(Event(batch, "appear", key))
                progressed = True
        return change


__all__ = ["ABSENT", "DONE", "HIDDEN", "OPEN", "Change", "Event", "Ledger", "SynthesisError"]
