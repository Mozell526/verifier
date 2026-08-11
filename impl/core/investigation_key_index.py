from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from impl.core.schema.investigation_key_index import (
    InvestigationKeyEntry,
    InvestigationKeyIndex,
    validate_investigation_key_index,
)
from impl.tools import ToolResult, VerifiableTool


class KeyIndexTargetResolver(Protocol):
    def __call__(self, target_ref: str) -> Mapping[str, Any]: ...


class KeyIndexTargetValidator(Protocol):
    def __call__(self, target_ref: str) -> None: ...


class KeyIndexSearchStrategy(Protocol):
    def __call__(
        self,
        query: str,
        entries: Sequence[InvestigationKeyEntry],
        limit: int,
    ) -> Sequence[tuple[InvestigationKeyEntry, float | None]]: ...


@dataclass(frozen=True)
class KeyIndexSearchHit:
    index_key: str
    key: str
    name: str
    target_ref: str
    score: float | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "index_key": self.index_key,
            "key": self.key,
            "name": self.name,
            "target_ref": self.target_ref,
        }
        if self.score is not None:
            result["score"] = self.score
        return result


@dataclass(frozen=True)
class KeyIndexReceipt:
    operation: str
    index_key: str
    key: str = ""
    query: str = ""
    target_refs: tuple[str, ...] = ()
    resolved_locator: str = ""
    load_targets: tuple[str, ...] = ()
    target_resolution: Any = None
    provenance: Any = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "operation": self.operation,
            "index_key": self.index_key,
        }
        if self.key:
            result["key"] = self.key
        if self.query:
            result["query"] = self.query
        if self.target_refs:
            result["target_refs"] = list(self.target_refs)
        if self.resolved_locator:
            result["resolved_locator"] = self.resolved_locator
        if self.load_targets:
            result["load_targets"] = list(self.load_targets)
        if self.target_resolution is not None:
            result["target_resolution"] = self.target_resolution
        if self.provenance is not None:
            result["provenance"] = self.provenance
        return result


@dataclass(frozen=True)
class _RegisteredIndex:
    index: InvestigationKeyIndex
    resolver: KeyIndexTargetResolver
    search_strategy: KeyIndexSearchStrategy


class InvestigationKeyIndexRegistry:
    """Generic navigation registry; it never interprets target business meaning."""

    def __init__(self) -> None:
        self._indexes: dict[str, _RegisteredIndex] = {}

    def register(
        self,
        index: InvestigationKeyIndex,
        *,
        resolver: KeyIndexTargetResolver,
        search_strategy: KeyIndexSearchStrategy,
        target_validator: KeyIndexTargetValidator | None = None,
    ) -> None:
        validate_investigation_key_index(index)
        if index.index_key in self._indexes:
            raise ValueError(f"key index already registered: {index.index_key}")
        if target_validator is not None:
            for entry in index.entries:
                target_validator(entry.target_ref)
        self._indexes[index.index_key] = _RegisteredIndex(
            index=index,
            resolver=resolver,
            search_strategy=search_strategy,
        )

    def index(self, index_key: str) -> InvestigationKeyIndex:
        try:
            return self._indexes[index_key].index
        except KeyError as exc:
            raise KeyError(f"key index not registered: {index_key}") from exc

    def catalog(self) -> tuple[dict[str, str], ...]:
        """Return navigation metadata only; entries and search text are excluded."""
        return tuple(
            {
                "index_key": registered.index.index_key,
                "collection_ref": registered.index.collection_ref,
                "target_kind": registered.index.target_kind,
                "entry_granularity": registered.index.entry_granularity,
            }
            for _, registered in sorted(self._indexes.items())
        )

    def search(
        self,
        index_key: str,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[list[KeyIndexSearchHit], KeyIndexReceipt]:
        registered = self._registered(index_key)
        query_text = str(query or "").strip()
        bounded_limit = max(1, min(int(limit), 32))
        ranked = list(
            registered.search_strategy(
                query_text,
                registered.index.entries,
                bounded_limit,
            )
        )[:bounded_limit]
        known = {entry.key: entry for entry in registered.index.entries}
        hits: list[KeyIndexSearchHit] = []
        seen: set[str] = set()
        for entry, score in ranked:
            canonical = known.get(entry.key)
            if canonical is None or canonical != entry:
                raise ValueError(
                    f"search strategy returned an entry outside index {index_key}: {entry.key}"
                )
            if entry.key in seen:
                continue
            seen.add(entry.key)
            hits.append(
                KeyIndexSearchHit(
                    index_key=index_key,
                    key=entry.key,
                    name=entry.name,
                    target_ref=entry.target_ref,
                    score=score,
                )
            )
        receipt = KeyIndexReceipt(
            operation="search_index",
            index_key=index_key,
            query=query_text,
            target_refs=tuple(hit.target_ref for hit in hits),
        )
        return hits, receipt

    def load(
        self,
        index_key: str,
        key: str,
    ) -> tuple[dict[str, Any], KeyIndexReceipt]:
        registered = self._registered(index_key)
        key_text = str(key or "").strip()
        if not key_text or "*" in key_text:
            raise ValueError("load_entry requires one explicit non-wildcard key")
        entry = next(
            (item for item in registered.index.entries if item.key == key_text),
            None,
        )
        if entry is None:
            raise KeyError(f"key index entry not found: {index_key}/{key_text}")
        resolved = dict(registered.resolver(entry.target_ref))
        if "content" not in resolved:
            raise ValueError(
                f"target resolver must return content: {index_key}/{key_text}"
            )
        locator = str(resolved.get("locator") or entry.target_ref)
        raw_load_targets = resolved.get("load_targets", ())
        if isinstance(raw_load_targets, (str, bytes)) or not isinstance(
            raw_load_targets, Sequence
        ):
            raise ValueError(
                f"target resolver load_targets must be a sequence: {index_key}/{key_text}"
            )
        load_targets = tuple(
            dict.fromkeys(
                str(item).strip() for item in raw_load_targets if str(item).strip()
            )
        )
        target_resolution = resolved.get("target_resolution")
        result = {
            "index_key": index_key,
            "key": entry.key,
            "name": entry.name,
            "target_ref": entry.target_ref,
            "content": resolved["content"],
            "locator": locator,
        }
        if load_targets:
            result["load_targets"] = list(load_targets)
        if target_resolution is not None:
            result["target_resolution"] = target_resolution
        if "provenance" in resolved:
            result["provenance"] = resolved["provenance"]
        receipt = KeyIndexReceipt(
            operation="load_entry",
            index_key=index_key,
            key=entry.key,
            target_refs=(entry.target_ref,),
            resolved_locator=locator,
            load_targets=load_targets,
            target_resolution=target_resolution,
            provenance=resolved.get("provenance"),
        )
        return result, receipt

    def _registered(self, index_key: str) -> _RegisteredIndex:
        key = str(index_key or "").strip()
        try:
            return self._indexes[key]
        except KeyError as exc:
            raise KeyError(f"key index not registered: {key}") from exc


def create_key_index_tools(
    registry: InvestigationKeyIndexRegistry,
) -> tuple[VerifiableTool, VerifiableTool]:
    catalog = registry.catalog()
    index_keys = [item["index_key"] for item in catalog]
    catalog_lines = [
        (
            f"{item['index_key']} [collection_ref={item['collection_ref']}; "
            f"target_kind={item['target_kind']}; "
            f"entry_granularity={item['entry_granularity']}]"
        )
        for item in catalog
    ]
    catalog_description = "Available indexes: " + "; ".join(catalog_lines)
    index_key_parameter: dict[str, Any] = {
        "type": "string",
        "description": (
            "Choose zero, one, or multiple indexes across separate calls according to the "
            "current subquestion. Do not guess unregistered keys. " + catalog_description
        ),
    }
    if index_keys:
        index_key_parameter["enum"] = index_keys

    def search_index(**kwargs: Any) -> ToolResult:
        try:
            hits, receipt = registry.search(
                str(kwargs.get("index_key") or ""),
                str(kwargs.get("query") or ""),
                limit=int(kwargs.get("limit") or 8),
            )
            return ToolResult(
                tool_id="investigation.search_index",
                tool_type="investigation_key_index_search",
                status="succeeded",
                actual={"candidates": [hit.as_dict() for hit in hits]},
                evidence="searched a registered investigation key index",
                runtime_metadata={"receipt": receipt.as_dict()},
            )
        except Exception as exc:
            return ToolResult(
                tool_id="investigation.search_index",
                tool_type="investigation_key_index_search",
                status="failed",
                error=str(exc),
            )

    def load_entry(**kwargs: Any) -> ToolResult:
        try:
            actual, receipt = registry.load(
                str(kwargs.get("index_key") or ""),
                str(kwargs.get("key") or ""),
            )
            return ToolResult(
                tool_id="investigation.load_entry",
                tool_type="investigation_key_index_load",
                status="succeeded",
                actual=actual,
                evidence="loaded the target of one registered key-index entry",
                runtime_metadata={"receipt": receipt.as_dict()},
            )
        except Exception as exc:
            return ToolResult(
                tool_id="investigation.load_entry",
                tool_type="investigation_key_index_load",
                status="failed",
                error=str(exc),
            )

    return (
        VerifiableTool(
            tool_id="investigation.search_index",
            description=(
                "Search one registered investigation navigation index for limited candidates. "
                "Indexes have no default parent/child relation or required order. "
                + catalog_description
            ),
            applicable_scenario="find candidate targets without loading the full collection",
            parameters={
                "type": "object",
                "properties": {
                    "index_key": dict(index_key_parameter),
                    "query": {"type": "string", "description": "Navigation query."},
                    "limit": {"type": "integer", "description": "Maximum candidate count."},
                },
                "required": ["index_key", "query"],
            },
            execute_fn=search_index,
        ),
        VerifiableTool(
            tool_id="investigation.load_entry",
            description=("Load one indexed target and, when deterministically resolvable in the "
                        "current runtime, return top-level load_targets for precise loading."),
            applicable_scenario="inspect one candidate target after search",
            parameters={
                "type": "object",
                "properties": {
                    "index_key": dict(index_key_parameter),
                    "key": {"type": "string", "description": "One explicit entry key."},
                },
                "required": ["index_key", "key"],
            },
            execute_fn=load_entry,
        ),
    )
