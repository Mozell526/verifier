"""client_search Draft-only field-key lookup.

The generic Judge protocol receives project tools opaquely. This module owns the
client_search-specific candidate lookup and its YAML-backed short-name policy.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from impl.core.investigation_key_index import InvestigationKeyIndexRegistry
from impl.core.schema import InvestigationKeyEntry, InvestigationKeyIndex, ProjectSpec
from impl.tools import ToolResult, VerifiableTool

from impl.projects.client_search.field_provider import (
    ClientSearchFieldDefinitionProvider,
)


_IGNORED_QUERY_CHARS = set("客户的有是和与及或并且一个哪些名单帮我找查询")


def _searchable_chars(value: Any) -> set[str]:
    return {
        char
        for char in str(value or "").casefold()
        if (
            not char.isspace()
            and char not in _IGNORED_QUERY_CHARS
            and (char.isalpha() or "\u4e00" <= char <= "\u9fff")
        )
    }


def _short_name(value: Any) -> str:
    short_name = (
        str(value or "").strip().split("，", 1)[0].split("。", 1)[0].strip()
    )
    for prefix in ("仅表示", "表示"):
        if short_name.startswith(prefix):
            short_name = short_name[len(prefix):].strip()
            break
    return short_name[:32]


@lru_cache(maxsize=8)
def _load_versioned_field_key_index(
    path: str,
    modified_ns: int,
    size: int,
) -> InvestigationKeyIndex:
    # modified_ns/size version the deterministic projection without copying
    # source content into the runtime prompt.
    del modified_ns, size
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    entries: list[InvestigationKeyEntry] = []
    seen_fields: set[str] = set()
    for raw in payload.get("intents", []) or []:
        if not isinstance(raw, dict):
            continue
        field = str(raw.get("field") or "").strip()
        if not field or field in seen_fields:
            continue
        seen_fields.add(field)
        entries.append(InvestigationKeyEntry(
            key=field,
            name=_short_name(raw.get("description")) or field,
            search_text=" ".join(
                str(raw.get(key) or "")
                for key in ("field", "retrieval_text", "description")
            ),
            target_ref=f"client-search-field://{field}",
        ))
    return InvestigationKeyIndex(
        index_key="client-search.field-definitions",
        collection_ref="business-field-definitions",
        target_kind="evidence_locator",
        entry_granularity="yaml_field_definition",
        entries=tuple(entries),
    )


def load_explicit_field_support(spec: ProjectSpec, field: str) -> tuple[bool, bool]:
    """Return (supported, explicit) from every source entry for one field."""
    path = spec.source_path("field_definitions")
    if not path:
        return True, False
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    flags = [
        item.get("is_supported")
        for item in (payload.get("intents") or [])
        if isinstance(item, dict)
        and str(item.get("field") or "").strip() == field
        and "is_supported" in item
    ]
    if not flags:
        return True, False
    return all(flag is not False for flag in flags), True


def _load_field_key_index(spec: ProjectSpec) -> InvestigationKeyIndex:
    path = spec.source_path("field_definitions")
    if not path:
        raise ValueError(
            f"Field definitions not configured for project {spec.project_id}"
        )
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Field definitions file not found: {path}")
    stat = source.stat()
    return _load_versioned_field_key_index(
        str(source.resolve()),
        stat.st_mtime_ns,
        stat.st_size,
    )


def _field_search_strategy(query, entries, limit):
    query_text = str(query or "").strip()
    query_chars = _searchable_chars(query_text)
    if not query_chars:
        return []
    candidates = []
    for entry in entries:
        score = len(query_chars & _searchable_chars(entry.search_text))
        if entry.key.casefold() in query_text.casefold():
            score += 100
        if "岁" in query_text or "周岁" in query_text:
            if "年龄" in entry.name or "age" in entry.key.casefold():
                score += 20
            if "family" in entry.key.casefold():
                score -= 5
        if score >= 2:
            candidates.append((entry, float(score)))
    candidates.sort(key=lambda item: (-item[1], item[0].key))
    return candidates[:limit]


def build_field_key_index_registry(
    spec: ProjectSpec,
    provider: ClientSearchFieldDefinitionProvider | None = None,
) -> InvestigationKeyIndexRegistry:
    provider = provider or ClientSearchFieldDefinitionProvider(spec)
    index = _load_field_key_index(spec)
    known_fields = {entry.key for entry in index.entries}

    def validate_target(target_ref: str) -> None:
        prefix = "client-search-field://"
        if not target_ref.startswith(prefix) or target_ref[len(prefix):] not in known_fields:
            raise ValueError(f"invalid client_search field target_ref: {target_ref}")

    def resolve_target(target_ref: str) -> dict[str, Any]:
        validate_target(target_ref)
        field = target_ref.split("://", 1)[1]
        raw = provider.get_field_definition(field)
        if not raw:
            raise KeyError(f"field definition not found: {field}")
        raw = dict(raw)
        supported, explicit = load_explicit_field_support(spec, field)
        if explicit:
            raw["is_supported"] = supported
            raw["is_supported_explicit"] = True
        return {
            "content": raw,
            "locator": f"field_definitions_args.yaml#field={field}",
            "provenance": {
                "project_id": spec.project_id,
                "source_path": spec.source_path("field_definitions"),
            },
        }

    registry = InvestigationKeyIndexRegistry()
    registry.register(
        index,
        resolver=resolve_target,
        search_strategy=_field_search_strategy,
        target_validator=validate_target,
    )
    return registry


def search_field_key_index(
    spec: ProjectSpec,
    query: str,
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    """Project facade over the generic investigation key-index protocol."""
    registry = build_field_key_index_registry(spec)
    hits, _receipt = registry.search(
        "client-search.field-definitions",
        query,
        limit=max(1, min(int(limit), 8)),
    )
    return [
        {"field": hit.key, "short_name": hit.name}
        for hit in hits
    ]


def create_field_key_search_tool(
    spec: ProjectSpec,
    registry: InvestigationKeyIndexRegistry | None = None,
) -> VerifiableTool:
    def search_field_keys(**kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query") or "").strip()
        try:
            active_registry = registry or build_field_key_index_registry(spec)
            hits, receipt = active_registry.search(
                "client-search.field-definitions",
                query,
                limit=max(1, min(int(kwargs.get("limit") or 8), 8)),
            )
            candidates = [
                {"field": hit.key, "short_name": hit.name}
                for hit in hits
            ]
            return ToolResult(
                tool_id="client_search.field.search_keys",
                tool_type="client_search_field_key_retrieval",
                status="succeeded",
                actual={"query": query, "candidates": candidates},
                evidence=f"retrieved client_search field-key candidates for {query}",
                runtime_metadata={"receipt": receipt.as_dict()},
            )
        except Exception as exc:
            return ToolResult(
                tool_id="client_search.field.search_keys",
                tool_type="client_search_field_key_retrieval",
                status="failed",
                error=f"Error searching client_search field keys: {exc}",
            )

    search_field_keys.__name__ = "client_search_field_key_search"
    return VerifiableTool(
        tool_id="client_search.field.search_keys",
        description=(
            "根据 client_search 用户请求检索少量可能相关的字段 key 和短名称。"
            "本工具对外函数名是 client_search_field_search（旧名 investigation_search_index 已废弃）；"
            "短名称来自项目字段定义 YAML；只返回候选 key，不返回完整字段定义。"
        ),
        applicable_scenario="client_search-judge-planning",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户当前的自然语言客户搜索请求。",
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回的候选数量，默认 8。",
                },
            },
            "required": ["query"],
        },
        execute_fn=search_field_keys,
    )


def create_minimal_field_definition_tool(
    provider: ClientSearchFieldDefinitionProvider,
    registry: InvestigationKeyIndexRegistry | None = None,
) -> VerifiableTool:
    def lookup_definition(**kwargs: Any) -> ToolResult:
        field = str(kwargs.get("field") or "").strip()
        try:
            if registry is not None:
                loaded, receipt = registry.load("client-search.field-definitions", field)
                raw = loaded["content"]
            else:
                receipt = None
                raw = provider.get_field_definition(field)
                if raw:
                    raw = dict(raw)
                    supported, explicit = load_explicit_field_support(provider.spec, field)
                    if explicit:
                        raw["is_supported"] = supported
                        raw["is_supported_explicit"] = True
            if not raw:
                return ToolResult(
                    tool_id="field.search_definition",
                    tool_type="client_search_field_definition",
                    status="inconclusive",
                    actual={"field": field, "found": False},
                    evidence=f"field '{field}' not found",
                )
            definition = {
                "field": str(raw.get("field") or field),
                "operators": list(raw.get("operators") or []),
                "value_types": list(raw.get("value_types") or []),
                "is_supported": raw.get("is_supported") is not False,
            }
            description = _short_name(raw.get("description"))
            if description:
                definition["short_name"] = description
            enums = list(raw.get("enums") or [])
            if enums:
                definition["enums"] = enums[:5]
            if raw.get("unit"):
                definition["unit"] = raw["unit"]
            return ToolResult(
                tool_id="field.search_definition",
                tool_type="client_search_field_definition",
                status="succeeded",
                actual=definition,
                evidence=f"retrieved minimal definition for {field}",
                runtime_metadata=(
                    {"receipt": receipt.as_dict()} if receipt is not None else {}
                ),
            )
        except Exception as exc:
            return ToolResult(
                tool_id="field.search_definition",
                tool_type="client_search_field_definition",
                status="failed",
                error=f"Error retrieving field definition: {exc}",
            )

    lookup_definition.__name__ = "field_search_definition"
    return VerifiableTool(
        tool_id="field.search_definition",
        description="按字段 key 读取一个字段是否支持搜索、短名称、操作符、值类型及少量枚举。",
        applicable_scenario="client_search-judge",
        parameters={
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "从字段索引获得的精确 key。",
                },
            },
            "required": ["field"],
        },
        execute_fn=lookup_definition,
    )
