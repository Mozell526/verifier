"""证据就是本次 loop 里模型实际看到的工具返回。

不另建台账：ToolLoop 的 History.calls 已记下每次调用的参数、返回与批次，pre_tool 只看得到此前批次——
正是"同批拿到的不能当场引用"。这里只做三件事：给知识源调用的返回盖上 call_id、按 call_id 找回调用、逐字核对引句。
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Optional

from impl.core.tool_loop import Call, History, Hook
from impl.projects.llm_probe.material_tools import quote_in_text


def call_id(call: Call) -> str:
    return f"c{call.id}"


class StampCallId(Hook):
    """post_tool：知识源工具的返回加上 call_id，模型据此引用。"""

    def __init__(self, tools: Iterable[str]) -> None:
        self.tools = set(tools)

    def post_tool(self, history: History, call: Call) -> Any:
        if call.tool in self.tools and isinstance(call.result, Mapping):
            # 盖在最后：工具自己的返回里若也有 call_id 之类的键，不能把证据编号覆盖掉。
            return {**call.result, "call_id": call_id(call)}
        return call.result


def failed(call: Call) -> str:
    """调用失败的原因；工具以 {'error': …} 报错（ES/MCP/资料工具都这样）也算失败。"""
    if not call.ok:
        return call.error or call.denied
    if isinstance(call.result, Mapping) and call.result.get("error"):
        return str(call.result["error"])
    return ""


def find(history: History, ref: str, tools: set[str]) -> Optional[Call]:
    """此前批次里、属于知识源工具的那次调用。"""
    for call in history.calls:
        if call.tool in tools and call_id(call) == ref:
            return call
    return None


def _leaves(value: Any) -> list[str]:
    if isinstance(value, str):
        # 返回体本身可能是 JSON 字符串（MCP 常见）：原文里的换行转义成了 \n，也比对解出来的字段。
        out = [value]
        if value[:1] in "[{":
            try:
                out.extend(_leaves(json.loads(value)))
            except ValueError:
                pass
        return out
    if isinstance(value, Mapping):
        return [leaf for key, item in value.items() if key != "call_id" for leaf in _leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaves(item)]
    return []


def quote_ok(call: Call, quote: str) -> bool:
    return any(quote_in_text(quote, leaf) for leaf in _leaves(call.result))


def window(call: Call, quote: str, chars: int = 500) -> str:
    """引句所在字段里，前后各 chars 字的原文；给下游判定看上下文（条件、例外常在引句旁边）。"""
    target = "".join(quote.split())
    for leaf in _leaves(call.result):
        compact, index = [], []
        for i, ch in enumerate(leaf):
            if not ch.isspace():
                compact.append(ch)
                index.append(i)
        at = "".join(compact).find(target)
        if target and at >= 0:
            start, end = index[at], index[at + len(target) - 1] + 1
            return leaf[max(0, start - chars):end + chars]
    return ""
