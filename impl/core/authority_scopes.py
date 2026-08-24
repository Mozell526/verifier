"""Authority enabled_scopes: two families, no boolean switch.

capability_carrier 走独立判后工具；其余四个走通用 in-run 通道。
空列表 = 全关。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

AUTHORITY_SCOPES = (
    "capability_carrier",
    "responsibility",
    "semantic_mapping",
    "query_equivalence",
    "conflict_arbitration",
)
IN_RUN_AUTHORITY_SCOPES = frozenset(AUTHORITY_SCOPES[1:])
CAPABILITY_CARRIER_SCOPE = "capability_carrier"


class AuthorityScopeRejected(ValueError):
    """Request named a scope that is not in enabled_scopes."""


def _authority_mapping(source: Any) -> Mapping[str, Any]:
    if source is None:
        return {}
    spec = getattr(source, "spec", None)
    if spec is not None and spec is not source:
        mapped = _authority_mapping(spec)
        if mapped:
            return mapped
    verifier = getattr(source, "verifier", None)
    if isinstance(verifier, Mapping):
        return verifier.get("authority") or {}
    if not isinstance(source, Mapping):
        return {}
    if "enabled_scopes" in source:
        return source
    if "authority" in source:
        return source.get("authority") or {}
    nested = source.get("verifier")
    if isinstance(nested, Mapping):
        return nested.get("authority") or {}
    return {}


def enabled_scopes(source: Any) -> tuple[str, ...]:
    raw = _authority_mapping(source).get("enabled_scopes") or []
    if not isinstance(raw, (list, tuple)):
        raise TypeError("verifier.authority.enabled_scopes must be a list")
    scopes: list[str] = []
    seen: set[str] = set()
    for item in raw:
        scope = str(item or "").strip()
        if not scope:
            continue
        if scope not in AUTHORITY_SCOPES:
            raise ValueError(f"unknown authority scope: {scope}")
        if scope in seen:
            continue
        seen.add(scope)
        scopes.append(scope)
    return tuple(scopes)


def scope_enabled(source: Any, scope: str) -> bool:
    return scope in enabled_scopes(source)


def in_run_authority_enabled(source: Any) -> bool:
    return any(scope in IN_RUN_AUTHORITY_SCOPES for scope in enabled_scopes(source))


def capability_carrier_enabled(source: Any) -> bool:
    return CAPABILITY_CARRIER_SCOPE in enabled_scopes(source)


def require_in_run_scope(source: Any, question_class: str) -> str:
    scope = str(question_class or "").strip()
    if scope not in IN_RUN_AUTHORITY_SCOPES:
        raise AuthorityScopeRejected(
            f"authority.resolve question_class must be one of "
            f"{sorted(IN_RUN_AUTHORITY_SCOPES)}; got {question_class!r}"
        )
    if scope not in enabled_scopes(source):
        raise AuthorityScopeRejected(
            f"authority.resolve question_class={scope!r} is not in enabled_scopes"
        )
    return scope


def parse_enabled_scopes(value: Any, path: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{path} must be a list")
    scopes: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        scope = str(item or "").strip()
        if not scope:
            raise ValueError(f"{path}[{index}] must be a non-empty string")
        if scope not in AUTHORITY_SCOPES:
            raise ValueError(f"{path}[{index}] unknown authority scope: {scope}")
        if scope in seen:
            continue
        seen.add(scope)
        scopes.append(scope)
    return scopes


def in_run_scopes(source: Any) -> tuple[str, ...]:
    return tuple(scope for scope in enabled_scopes(source) if scope in IN_RUN_AUTHORITY_SCOPES)
