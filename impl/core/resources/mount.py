"""挂载与读取（spec/alg/resources.md §4）：一个 case 一张资源表，由各信息源的 ``mount`` 往里挂直接资源。

对外的读法照 MCP：``list`` = ``resources/list``（直接资源的描述），``templates`` = ``resources/templates/list``
（各资源类型声明的模板），``read`` = ``resources/read``（直接资源、模板资源都按地址读）。
MCP 没有层级目录；这里每个上级路径是一个自动生成的目录资源（``inode/directory``），读它返回下一级各项的描述。
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from mcp.types import ReadResourceResult, Resource, ResourceTemplate, TextResourceContents

from .spec import TYPE_KEY, Address, Block
from .types import TYPES

DIRECTORY = "inode/directory"


class ResourceTable:
    def __init__(self) -> None:
        self._items: dict[str, Block] = {}

    def mount(self, uri: str, type: str, body: Any, *, name: str, title: str | None = None,
              description: str | None = None, meta: Mapping[str, Any] | None = None) -> Block:
        """挂一个直接资源：信息源给地址、类型、正文与目录标签；``mimeType``、``size`` 由类型算，类型名记进 ``_meta``。"""
        address = str(Address.parse(uri))
        if type not in TYPES:
            raise ValueError(f"未知资源类型 {type!r}；可用：{sorted(TYPES)}")
        kind = TYPES[type]
        descriptor = Resource(uri=uri, name=name, title=title, description=description, mimeType=kind.mime_type,
                              size=len(kind.text(body).encode()), _meta={**(meta or {}), TYPE_KEY: type})
        if str(descriptor.uri) != address:
            raise ValueError(f"地址不合 RFC 3986（会被改写成 {descriptor.uri}）：{uri}")
        if address in self._items:
            raise ValueError(f"同一地址只能挂一次：{uri}")
        if self._is_directory(address) or any(address.startswith(key + "/") for key in self._items):
            raise ValueError(f"直接资源不能互为上下级：{uri}")
        block = self._items[address] = Block(descriptor, body)
        return block

    def get(self, uri: str) -> Block | None:
        return self._items.get(str(Address.parse(uri)))

    def part(self, uri: str) -> tuple[Block, str] | None:
        """地址所指的资源：直接资源 → (这一块, "")；模板资源 → (所属那一块, 块里的节点)；都不是返回 None。"""
        address = str(Address.parse(uri))
        if address in self._items:
            return self._items[address], ""
        for name, kind in TYPES.items():
            hit = kind.resolve(address)
            block = self._items.get(hit[0]) if hit else None
            if block is not None and block.type == name:
                return block, hit[1]
        return None

    def list(self) -> list[Resource]:
        return [block.descriptor for block in self._items.values()]

    def templates(self) -> list[ResourceTemplate]:
        used = sorted({(block.type, Address.parse(block.uri).scheme) for block in self._items.values()})
        return [t for name, scheme in used for t in TYPES[name].templates(scheme)]

    def read(self, uri: str) -> ReadResourceResult:
        address = str(Address.parse(uri))
        part = self.part(address)
        if part is not None:
            block, node = part
            return ReadResourceResult(contents=[TYPES[block.type].read(block, node, address)])
        if not self._is_directory(address):
            raise LookupError(f"资源不存在：{uri}")
        listing = [d.model_dump(mode="json", by_alias=True, exclude_none=True) for d in self._children(address)]
        return ReadResourceResult(contents=[TextResourceContents(
            uri=address, mimeType=DIRECTORY, text=json.dumps(listing, ensure_ascii=False))])

    def _is_directory(self, address: str) -> bool:
        return any(key.startswith(address + "/") for key in self._items)

    def _children(self, address: str) -> list[Resource]:
        prefix, out, folders = address + "/", [], {}
        for key, block in self._items.items():
            if not key.startswith(prefix):
                continue
            head, _, rest = key[len(prefix):].partition("/")
            if rest:
                folders.setdefault(head, Resource(uri=prefix + head, name=head, mimeType=DIRECTORY))
            else:
                out.append(block.descriptor)
        return list(folders.values()) + out

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items.values())
