"""引用核对的公共入口（spec/alg/resources.md §6）。

依次判：地址所指的资源存在 → 读过所属那一块 → 在引用范围内 → 在这个资源里找得到；找到即过。
资源是最小引用单位：命中几处都算过，如实报出各处所在节点与角色；一条引用够不够支撑结论由使用方判。
"在资源里找"按模型看到的那份文本做（读出来的与核对用的是同一份）；找不到时给最接近的一段作提示，不放行。
地址只收完整的资源地址，引用方自己把写法转成地址。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Collection, Mapping, Sequence

from .mount import ResourceTable
from .text import closest, render, smallest
from .types import TYPES
from .types.record_set import Role

HINT_CHARS = 60


@dataclass(frozen=True)
class Region:
    node: str                         # 包含命中的最小节点（这一块正文里的位置）
    start: int                        # 这一块规范文本上的区间；seen_only 时是看到的那份上的区间
    end: int
    seen_only: bool = False


@dataclass(frozen=True)
class CiteResult:
    ok: bool
    reason: str = ""                  # no_address / not_seen / out_of_scope / not_found
    address: str = ""                 # 地址所指的资源
    block: str = ""                   # 所属那一块（直接资源）的地址
    regions: Sequence[Region] = field(default_factory=tuple)
    roles: Sequence[Role] = field(default_factory=tuple)   # 各处命中的角色（去重、排序）
    hint: str = ""


def cite(table: ResourceTable, uri: str, quote: str, *, seen: Mapping[str, Sequence[Any]],
         scope: Collection[str] | None = None, view: str | None = None) -> CiteResult:
    """``seen``：块地址 → 这次提交之前模型看到的这一块的各份内容；``scope``：可引的块地址，None 为不限；
    ``view``：按哪个视角判角色（记录集：哪类环节的输入端 / 输出端）。"""
    try:
        part = table.part(uri)
    except ValueError:
        return CiteResult(False, "no_address", address=str(uri))
    if part is None:
        return CiteResult(False, "no_address", address=uri)
    block, node = part
    kind = TYPES[block.type]
    canonical, canonical_spans = render(block.body)
    if node and kind.slice(block.body, node) is None:
        return CiteResult(False, "no_address", address=uri, block=block.uri)
    versions = list(seen.get(block.uri) or [])
    if not versions:
        return CiteResult(False, "not_seen", address=uri, block=block.uri)
    if scope is not None and block.uri not in scope:
        return CiteResult(False, "out_of_scope", address=uri, block=block.uri)

    positions: dict[tuple, tuple] = {}   # 同一位置在几份看到的文本里重复出现算一处
    for version in versions:
        text = render(version)[0]
        for hit in kind.locate(block, quote, seen=version, node=node) or []:
            span = hit.node
            positions.setdefault((span.pointer, span.member, hit.start - span.start, hit.end - hit.start),
                                 (text, span, hit.start, hit.end))
    if not positions:
        return CiteResult(False, "not_found", address=uri, block=block.uri, hint=_hint(quote, versions))

    regions = []
    for (pointer, member, rel, length), (text, span, start, end) in positions.items():
        target = next((s for s in canonical_spans if s.pointer == pointer and s.member == member), None)
        seen_only = target is None or canonical[target.start:target.end] != text[span.start:span.end]
        if not seen_only:
            start, end = target.start + rel, target.start + rel + length
        regions.append(Region(pointer, start, end, seen_only))
    roles = tuple(sorted({kind.role(block, r.node, view) for r in regions}))
    return CiteResult(True, address=uri, block=block.uri, regions=tuple(regions), roles=roles)


def _hint(quote: str, versions: Sequence[Any]) -> str:
    best = None
    for version in versions:
        text, spans = render(version)
        found = closest(quote, text)
        if found and (best is None or found[1] - found[0] > best[0]):
            node = smallest(spans, *found)
            lo, hi = max(node.start, found[0] - 10), min(node.end, found[1] + HINT_CHARS)
            best = (found[1] - found[0], node.pointer, text[lo:hi])
    if best is None:
        return "这一块里没有相近的原文"
    return f"最接近的是 {best[1] or '/'} 里的：{best[2]}"
