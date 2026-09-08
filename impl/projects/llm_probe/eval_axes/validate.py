"""场景轴（预设 axes[]）的加载期校验（axe-v4 §7）。

保存时 capability_store.validate_entry 只校形状；类型是否注册、依赖是否启用、
资料引用能否按类型的展开方式展开，都在这里、在运行前查。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from impl.core.capability_store import load_capability_map
from impl.core.materials_store import expand_material_uris, expand_material_uris_with_catalog

from .registry import AXIS_TYPES, get_axis_type
from .types import EXPAND_CATALOG, TYPE_ID_PATTERN, AxisType, ScenarioAxis

MAX_DESCRIPTION_CHARS = 20000


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_for_errors(self, owner: str = "") -> None:
        if self.errors:
            prefix = f"{owner}: " if owner else ""
            raise ValueError(prefix + "扩展评估轴配置无效：" + "；".join(self.errors))


def parse_axes(raw: Any, *, owner: str = "axes") -> list[ScenarioAxis]:
    """只校形状（与 capability_store.validate_entry 的口径一致），不查注册表。"""
    if raw in (None, ""):
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{owner} 必须是列表")
    axes: list[ScenarioAxis] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"{owner}[{index}]"
        if not isinstance(item, Mapping):
            raise ValueError(f"{label} 必须是对象")
        type_id = str(item.get("type") or "").strip()
        if not TYPE_ID_PATTERN.fullmatch(type_id):
            raise ValueError(f"{label}.type 必须是小写标识符，得到 {type_id!r}")
        if type_id in seen:
            raise ValueError(f"{owner}: 同一类型 {type_id} 只允许一个框")
        seen.add(type_id)
        enabled = item.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError(f"{label}.enabled 必须是布尔值")
        description = item.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{label}.description 不能为空")
        if len(description) > MAX_DESCRIPTION_CHARS:
            raise ValueError(f"{label}.description 超过 {MAX_DESCRIPTION_CHARS} 字符上限")
        axes.append(ScenarioAxis(type_id=type_id, enabled=enabled, description=description.strip()))
    return axes


def _expand_description(axis_type: AxisType, description: str) -> None:
    mode = next((f.expand for f in axis_type.scenario_fields if f.name == "description"), None)
    if mode == EXPAND_CATALOG:
        expand_material_uris_with_catalog(description)
    else:
        expand_material_uris(description)


def validate_scenario_axes(axes: Sequence[ScenarioAxis]) -> ValidationReport:
    report = ValidationReport()
    by_type: dict[str, ScenarioAxis] = {}
    for axis in axes:
        if axis.type_id in by_type:
            report.errors.append(f"同一类型 {axis.type_id} 只允许一个框")
            continue
        by_type[axis.type_id] = axis
    for axis in axes:
        if axis.type_id not in AXIS_TYPES:
            report.errors.append(f"未注册的轴类型 {axis.type_id!r}")
            continue
        axis_type = AXIS_TYPES[axis.type_id]
        try:
            _expand_description(axis_type, axis.description)
        except ValueError as exc:
            report.errors.append(f"{axis.type_id}.description 资料引用无效: {exc}")
        if not axis.enabled:
            continue
        for upstream_id in axis_type.depend_on:
            upstream = by_type.get(upstream_id)
            if upstream is None:
                report.errors.append(f"{axis.type_id} 依赖 {upstream_id}，但本预设没有这个框")
            elif not upstream.enabled:
                report.errors.append(f"{axis.type_id} 依赖 {upstream_id}，但该框未启用")
        referenced = {slot.axis_ref for slot in axis_type.inputs if slot.axis_ref}
        if axis_type.trigger_when is not None:
            referenced.add(axis_type.trigger_when.axis)
        for upstream_id in axis_type.depend_on:
            if upstream_id not in referenced:
                report.warnings.append(
                    f"{axis.type_id} 声明依赖 {upstream_id}，但 trigger_when 和 inputs 都没引用它（纯排序依赖，通常多余）"
                )
    return report


def scenario_axes_from_entry(
    entry: Mapping[str, Any], *, owner: str = "",
) -> tuple[list[ScenarioAxis], ValidationReport]:
    """从一条 capability 预设条目取出校验过的场景轴；有错直接抛，警告随报告带回。"""
    axes = parse_axes(entry.get("axes") if isinstance(entry, Mapping) else None, owner=f"{owner}.axes" if owner else "axes")
    report = validate_scenario_axes(axes)
    report.raise_for_errors(owner)
    return axes, report


def load_scenario_axes(project_id: str, capability_ref: str) -> tuple[list[ScenarioAxis], ValidationReport]:
    ref = str(capability_ref or "").strip()
    if not ref:
        raise ValueError("样本缺 capability_ref，无法定位场景的扩展评估轴")
    entry = load_capability_map(project_id).get(ref)
    if not isinstance(entry, Mapping):
        raise ValueError(f"capability 预设 {ref} 不存在")
    return scenario_axes_from_entry(entry, owner=ref)


__all__ = [
    "MAX_DESCRIPTION_CHARS",
    "ValidationReport",
    "get_axis_type",
    "load_scenario_axes",
    "parse_axes",
    "scenario_axes_from_entry",
    "validate_scenario_axes",
]
