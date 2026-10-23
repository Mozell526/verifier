"""轴定义：一个轴 = 一条配置（spec/alg/axis_loop.md §3）。

存储 `axis_definitions.json`（与场景预设 capability_map.json 同目录、同一种存法，页面读写）：

    {"axes": {<id>: {...}}, "shared_tools": {<id>: {...}}}

输出写成 JSON Schema（type=object），顶层每个属性用 `x-fill: model | program` 标谁填，缺省 model。
代码只有三个固定插口（axis_code/<轴>/，公共 loop 工具在 axis_code/shared/<工具>/）：
checks.py 的 check(view)、synth.py 的 synthesize(view)、dispatch.py 的 dispatch(view)。
本模块只管解析与自洽；名字、路径、校验参数是否对得上注册表与场景，见 validate.py。
"""
from __future__ import annotations

import importlib.util
import inspect
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Optional

from impl.core import capability_store

FILL_MODEL, FILL_PROGRAM = "model", "program"
EXECUTOR_MODEL, EXECUTOR_PROGRAM = "model", "program"
RUN_MAIN, RUN_ISOLATED = "main", "isolated"
ROLE_ANALYSIS, ROLE_EVALUATION = "analysis", "evaluation"
SUBMIT_ONCE, SUBMIT_PER_ITEM = "once", "per_item"
STORE_NAME = "axis_definitions.json"
CODE_DIR = "axis_code"
_PLUGS = {"check": "checks.py", "synthesize": "synth.py", "dispatch": "dispatch.py"}


@dataclass(frozen=True)
class Dependency:
    axis: str
    hard: bool


@dataclass(frozen=True)
class Trigger:
    axis: str
    verdict_in: tuple[str, ...]


@dataclass(frozen=True)
class ToolCategory:
    category: str
    required: bool


@dataclass(frozen=True)
class CheckUse:
    name: str
    params: Mapping[str, Any]


@dataclass(frozen=True)
class Code:
    """上传的代码；没上传为 None。"""

    check: Optional[Callable[[Any], list]] = None
    synthesize: Optional[Callable[[Any], Mapping]] = None
    dispatch: Optional[Callable[[Any], list]] = None


@dataclass(frozen=True)
class Work:
    """轴与公共 loop 工具共有的部分：说明、材料、信息源、提交、输出、校验、代码。"""

    id: str
    instruction: str
    materials: tuple[str, ...]
    tool_categories: tuple[ToolCategory, ...]
    submit: str
    items_field: str
    item_key: str      # 分条交时分项的编号字段（submit 的 item_id 写进它）
    output: Mapping[str, Any]
    checks: tuple[CheckUse, ...]
    code: Code

    def fill(self, name: str) -> str:
        return str((self.output.get("properties") or {}).get(name, {}).get("x-fill") or FILL_MODEL)

    @property
    def program_fields(self) -> tuple[str, ...]:
        return tuple(n for n in self.output.get("properties") or {} if self.fill(n) == FILL_PROGRAM)

    def model_schema(self) -> dict[str, Any]:
        """模型交的那部分：去掉程序填的字段；分条交时再去掉分项列表（分项单独交）。"""
        drop = set(self.program_fields) | ({self.items_field} if self.submit == SUBMIT_PER_ITEM else set())
        props = {k: v for k, v in (self.output.get("properties") or {}).items() if k not in drop}
        required = [k for k in self.output.get("required") or [] if k not in drop]
        return {**self.output, "properties": props, "required": required}

    def item_schema(self) -> dict[str, Any]:
        """分条交时一个分项的 schema。"""
        return dict(((self.output.get("properties") or {}).get(self.items_field) or {}).get("items") or {})


@dataclass(frozen=True)
class SharedToolDef(Work):
    """公共 loop 工具：调用方的模型按 params 调用，内部是一个独立子 loop（§6.3）。"""

    description: str = ""
    params: Mapping[str, Any] = field(default_factory=dict)  # JSON Schema（type=object）


@dataclass(frozen=True)
class AxisDef(Work):
    title: str = ""
    executor: str = EXECUTOR_MODEL
    run_mode: str = RUN_MAIN
    role: str = ROLE_EVALUATION
    depends: tuple[Dependency, ...] = ()
    trigger: Optional[Trigger] = None
    tools: tuple[str, ...] = ()  # 选用的公共 loop 工具

    @property
    def verdict_values(self) -> tuple[str, ...]:
        verdict = (self.output.get("properties") or {}).get("verdict") or {}
        return tuple(verdict.get("enum") or ())

    @property
    def automatic(self) -> bool:
        """由程序推进、不推送给主 loop 模型的轴：程序任务与独立运行的轴。"""
        return self.executor == EXECUTOR_PROGRAM or self.run_mode == RUN_ISOLATED


@dataclass(frozen=True)
class Definitions:
    axes: Mapping[str, AxisDef]
    shared_tools: Mapping[str, SharedToolDef]


# ---- 读取 -------------------------------------------------------------------------------

def store_path(project_id: str) -> Path:
    return capability_store.store_path(project_id).with_name(STORE_NAME)


def code_dir(project_id: str) -> Path:
    return capability_store.store_path(project_id).with_name(CODE_DIR)


def _load_code(directory: Path, label: str) -> Code:
    found: dict[str, Callable] = {}
    for name, filename in _PLUGS.items():
        path = directory / filename
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"axis_code.{label.replace('/', '.')}.{path.stem}", path)
        module: ModuleType = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, name, None)
        if not callable(fn) or len(inspect.signature(fn).parameters) != 1:
            raise ValueError(f"{label}: {filename} 必须定义 {name}(view)")
        found[name] = fn
    return Code(**found)


def _strings(raw: Any, label: str) -> tuple[str, ...]:
    if raw in (None, ""):
        return ()
    if not isinstance(raw, list) or any(not isinstance(x, str) or not x.strip() for x in raw):
        raise ValueError(f"{label} 必须是非空字符串列表")
    return tuple(x.strip() for x in raw)


def _choice(raw: Any, default: str, allowed: tuple[str, ...], label: str) -> str:
    value = str(raw or default)
    if value not in allowed:
        raise ValueError(f"{label} 只能是 {' / '.join(allowed)}")
    return value


def _work(raw: Mapping[str, Any], label: str, code: Code) -> dict[str, Any]:
    output = raw.get("output")
    if not isinstance(output, Mapping) or output.get("type") != "object" or not isinstance(output.get("properties"), Mapping):
        raise ValueError(f"{label}.output 必须是 type=object 且带 properties 的 JSON Schema")
    checks = []
    for i, item in enumerate(raw.get("checks") or []):
        if not isinstance(item, Mapping) or len(item) != 1:
            raise ValueError(f"{label}.checks[{i}] 必须写成 {{校验名: 参数}}")
        (name, params), = item.items()
        if not isinstance(params, Mapping):
            raise ValueError(f"{label}.checks[{i}].{name} 的参数必须是对象")
        checks.append(CheckUse(str(name), dict(params)))
    cats = []
    for i, item in enumerate(raw.get("tool_categories") or []):
        if not isinstance(item, Mapping) or not str(item.get("category") or "").strip():
            raise ValueError(f"{label}.tool_categories[{i}] 必须有 category")
        cats.append(ToolCategory(str(item["category"]), bool(item.get("required"))))
    return dict(id=str(raw.get("id") or ""), instruction=str(raw.get("instruction") or ""),
                materials=_strings(raw.get("materials"), f"{label}.materials"), tool_categories=tuple(cats),
                submit=_choice(raw.get("submit"), SUBMIT_ONCE, (SUBMIT_ONCE, SUBMIT_PER_ITEM), f"{label}.submit"),
                items_field=str(raw.get("items_field") or ""), item_key=str(raw.get("item_key") or "item_id"),
                output=dict(output), checks=tuple(checks), code=code)


def parse_shared_tool(raw: Mapping[str, Any], *, code: Code) -> SharedToolDef:
    label = f"shared tool {raw.get('id')}"
    params = raw.get("params") or {}
    if params and (not isinstance(params, Mapping) or params.get("type") != "object"):
        raise ValueError(f"{label}.params 必须是 type=object 的 JSON Schema，或留空")
    return SharedToolDef(**_work(raw, label, code), description=str(raw.get("description") or ""), params=dict(params))


def parse_axis(raw: Mapping[str, Any], *, code: Code) -> AxisDef:
    label = f"axis {raw.get('id')}"
    depends = []
    for i, item in enumerate(raw.get("depends") or []):
        if not isinstance(item, Mapping) or not str(item.get("axis") or "").strip():
            raise ValueError(f"{label}.depends[{i}] 必须有 axis")
        depends.append(Dependency(str(item["axis"]), bool(item.get("hard"))))
    trigger = raw.get("trigger")
    if trigger is not None:
        if not isinstance(trigger, Mapping) or not trigger.get("axis") or not trigger.get("verdict_in"):
            raise ValueError(f"{label}.trigger 必须写成 {{axis, verdict_in}}")
        trigger = Trigger(str(trigger["axis"]), _strings(trigger["verdict_in"], f"{label}.trigger.verdict_in"))
    return AxisDef(**_work(raw, label, code), title=str(raw.get("title") or raw.get("id") or ""),
                   executor=_choice(raw.get("executor"), EXECUTOR_MODEL, (EXECUTOR_MODEL, EXECUTOR_PROGRAM), f"{label}.executor"),
                   run_mode=_choice(raw.get("run_mode"), RUN_MAIN, (RUN_MAIN, RUN_ISOLATED), f"{label}.run_mode"),
                   role=_choice(raw.get("role"), ROLE_EVALUATION, (ROLE_ANALYSIS, ROLE_EVALUATION), f"{label}.role"),
                   depends=tuple(depends), trigger=trigger, tools=_strings(raw.get("tools"), f"{label}.tools"))


def parse(raw: Mapping[str, Any], code_root: Optional[Path] = None) -> Definitions:
    """存储内容 → Definitions。code_root 下按 §3.1 的目录找上传的代码；None = 没有代码。"""
    if not isinstance(raw, Mapping):
        raise ValueError("轴定义存储必须是对象")
    unknown = set(raw) - {"axes", "shared_tools"}
    if unknown:
        raise ValueError(f"轴定义存储只认 axes / shared_tools，多了 {sorted(unknown)}")

    def code_at(*parts: str) -> Code:
        return _load_code(code_root.joinpath(*parts), "/".join(parts)) if code_root else Code()

    axes = {key: parse_axis({**item, "id": key}, code=code_at(key)) for key, item in (raw.get("axes") or {}).items()}
    shared = {key: parse_shared_tool({**item, "id": key}, code=code_at("shared", key))
              for key, item in (raw.get("shared_tools") or {}).items()}
    return Definitions(axes=axes, shared_tools=shared)


def load(project_id: str) -> Definitions:
    path = store_path(project_id)
    if not path.is_file():
        raise ValueError(f"{project_id}: 没有轴定义存储 {path}")
    return parse(json.loads(path.read_text(encoding="utf-8")), code_dir(project_id))
