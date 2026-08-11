from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


_FORBIDDEN_ENTRY_FIELDS = {
    "authority_status",
    "authority_resolution",
    "judge_verdict",
    "verdict",
    "expected",
    "expected_answer",
    "fulfilled",
    "resolved",
}

_FORBIDDEN_INDEX_FIELDS = {
    "use_when",
    "next_index",
    "next_index_key",
    "priority",
    "recommended_query",
    "recommended_queries",
}


def _required_text(value: Any, field_path: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_path} is required")
    return text


@dataclass(frozen=True)
class InvestigationKeyEntry:
    key: str
    name: str
    search_text: str
    target_ref: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InvestigationKeyEntry":
        if not isinstance(value, Mapping):
            raise TypeError("InvestigationKeyEntry must be an object")
        forbidden = sorted(_FORBIDDEN_ENTRY_FIELDS & set(value))
        if forbidden:
            raise ValueError(
                "InvestigationKeyEntry cannot carry business conclusions: "
                + ", ".join(forbidden)
            )
        allowed = {"key", "name", "search_text", "target_ref"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "InvestigationKeyEntry has unknown fields: " + ", ".join(unknown)
            )
        return cls(
            key=_required_text(value.get("key"), "InvestigationKeyEntry.key"),
            name=_required_text(value.get("name"), "InvestigationKeyEntry.name"),
            search_text=_required_text(
                value.get("search_text"), "InvestigationKeyEntry.search_text"
            ),
            target_ref=_required_text(
                value.get("target_ref"), "InvestigationKeyEntry.target_ref"
            ),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "name": self.name,
            "search_text": self.search_text,
            "target_ref": self.target_ref,
        }


@dataclass(frozen=True)
class InvestigationKeyIndex:
    index_key: str
    collection_ref: str
    target_kind: str
    entry_granularity: str
    entries: tuple[InvestigationKeyEntry, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InvestigationKeyIndex":
        if not isinstance(value, Mapping):
            raise TypeError("InvestigationKeyIndex must be an object")
        forbidden = sorted(_FORBIDDEN_INDEX_FIELDS & set(value))
        if forbidden:
            raise ValueError(
                "InvestigationKeyIndex cannot carry runtime routing hints: "
                + ", ".join(forbidden)
            )
        allowed = {
            "index_key",
            "collection_ref",
            "target_kind",
            "entry_granularity",
            "entries",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "InvestigationKeyIndex has unknown fields: " + ", ".join(unknown)
            )
        entries = value.get("entries") or []
        if not isinstance(entries, list):
            raise TypeError("InvestigationKeyIndex.entries must be a list")
        index = cls(
            index_key=_required_text(
                value.get("index_key"), "InvestigationKeyIndex.index_key"
            ),
            collection_ref=_required_text(
                value.get("collection_ref"), "InvestigationKeyIndex.collection_ref"
            ),
            target_kind=_required_text(
                value.get("target_kind"), "InvestigationKeyIndex.target_kind"
            ),
            entry_granularity=_required_text(
                value.get("entry_granularity"),
                "InvestigationKeyIndex.entry_granularity",
            ),
            entries=tuple(InvestigationKeyEntry.from_dict(item) for item in entries),
        )
        validate_investigation_key_index(index)
        return index

    def as_dict(self) -> dict[str, Any]:
        return {
            "index_key": self.index_key,
            "collection_ref": self.collection_ref,
            "target_kind": self.target_kind,
            "entry_granularity": self.entry_granularity,
            "entries": [entry.as_dict() for entry in self.entries],
        }


def validate_investigation_key_index(index: InvestigationKeyIndex) -> None:
    _required_text(index.index_key, "InvestigationKeyIndex.index_key")
    _required_text(index.collection_ref, "InvestigationKeyIndex.collection_ref")
    _required_text(index.target_kind, "InvestigationKeyIndex.target_kind")
    _required_text(
        index.entry_granularity, "InvestigationKeyIndex.entry_granularity"
    )
    seen: set[str] = set()
    for entry in index.entries:
        InvestigationKeyEntry.from_dict(entry.as_dict())
        if entry.key in seen:
            raise ValueError(
                f"duplicate InvestigationKeyEntry key in {index.index_key}: {entry.key}"
            )
        seen.add(entry.key)


def validate_investigation_key_indexes(
    indexes: list[InvestigationKeyIndex] | tuple[InvestigationKeyIndex, ...],
) -> None:
    seen: set[str] = set()
    for index in indexes:
        validate_investigation_key_index(index)
        if index.index_key in seen:
            raise ValueError(
                f"duplicate InvestigationKeyIndex.index_key: {index.index_key}"
            )
        seen.add(index.index_key)
