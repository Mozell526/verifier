"""轴类型清单：来自轴定义存储（spec/alg/axis_loop.md §3），给资料页下拉、表格视图与场景校验用。

与 llm_probe 的 eval_axes.registry 同名同用法（service、table_view、capability 按项目名取这里）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from impl.core.axis_loop.definitions import AxisDef, Definitions, load

PROJECT = "llm_probe_loop"
TRACE = "trace"  # 需要业务 trace 的轴声明这一类信息源（spec/alg/axis_loop.md §8）


@dataclass(frozen=True)
class AxisInfo:
    type_id: str
    title: str
    role: str
    axis: AxisDef

    @property
    def requires_business_trace(self) -> bool:
        return any(c.category == TRACE and c.required for c in self.axis.tool_categories)

    def describe(self) -> dict[str, Any]:
        a = self.axis
        return {"type": self.type_id, "title": self.title, "role": self.role, "executor": a.executor, "run_mode": a.run_mode,
                "depend_on": [{"type_id": d.axis, "optional": not d.hard} for d in a.depends],
                "trigger_when": {"axis": a.trigger.axis, "verdict_in": list(a.trigger.verdict_in)} if a.trigger else None,
                "verdict_enum": [{"value": v} for v in a.verdict_values], "materials": list(a.materials)}


def definitions() -> Definitions:
    return load(PROJECT)


def axis_types() -> Mapping[str, AxisInfo]:
    return {key: AxisInfo(key, axis.title, axis.role, axis) for key, axis in definitions().axes.items()}


class _Lazy(Mapping):
    """AXIS_TYPES：每次读都按当前存储算（页面改了定义不用重启）。"""

    def __getitem__(self, key):
        return axis_types()[key]

    def __iter__(self):
        return iter(axis_types())

    def __len__(self):
        return len(axis_types())


AXIS_TYPES: Mapping[str, AxisInfo] = _Lazy()


def describe_axis_types() -> list[dict[str, Any]]:
    return [info.describe() for info in axis_types().values()]
