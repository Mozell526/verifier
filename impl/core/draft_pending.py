"""Draft Loop pending list: exclusions, waivers, stale feedback. 3-round cap."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

PENDING_SCHEMA_VERSION = 1
PENDING_ROLL_LIMIT = 3
PENDING_KINDS = ("excluded_case", "criterion_waiver", "stale_gate_feedback")
PENDING_ROUTES = ("investigate", "solidify", "human")


def pending_path(state_dir: Path) -> Path:
    return Path(state_dir) / "pending.json"


def load_pending(state_dir: Path) -> dict[str, Any]:
    path = pending_path(state_dir)
    if not path.is_file():
        return {"schema_version": PENDING_SCHEMA_VERSION, "items": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError(f"pending.json must be an object: {path}")
    items = raw.get("items") or []
    if not isinstance(items, list):
        raise TypeError("pending.items must be a list")
    return {"schema_version": PENDING_SCHEMA_VERSION, "items": list(items)}


def save_pending(
    state_dir: Path,
    payload: Mapping[str, Any],
    *,
    repository_root: Path | None = None,
) -> Path:
    from .portable_artifact import project_artifact_repository_root, write_active_artifact

    path = pending_path(state_dir)
    root = repository_root or project_artifact_repository_root(path)
    if root is None:
        raise ValueError("pending.json must be written inside a verifier project package")
    return write_active_artifact(
        "draft_pending",
        path,
        dict(payload),
        repository_root=root,
    )


def _item_id(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def upsert_items(
    items: list[dict[str, Any]],
    *,
    kind: str,
    key: str,
    reason: str,
    route: str,
    iteration: int,
) -> list[dict[str, Any]]:
    if kind not in PENDING_KINDS:
        raise ValueError(f"unknown pending kind: {kind}")
    if route not in PENDING_ROUTES:
        raise ValueError(f"unknown pending route: {route}")
    item_id = _item_id(kind, key)
    for item in items:
        if item.get("id") == item_id:
            item["reason"] = reason
            item["route"] = route
            return items
    items.append({
        "id": item_id,
        "kind": kind,
        "key": key,
        "reason": reason,
        "route": route,
        "first_iteration": iteration,
        "extensions": 0,
    })
    return items


def clear_item(items: list[dict[str, Any]], kind: str, key: str) -> list[dict[str, Any]]:
    item_id = _item_id(kind, key)
    return [item for item in items if item.get("id") != item_id]


def extend_item(items: list[dict[str, Any]], item_id: str) -> list[dict[str, Any]]:
    found = False
    for item in items:
        if item.get("id") == item_id:
            item["extensions"] = int(item.get("extensions") or 0) + 1
            found = True
    if not found:
        raise ValueError(f"pending item not found: {item_id}")
    return items


def overdue_items(items: Sequence[Mapping[str, Any]], current_iteration: int) -> list[dict[str, Any]]:
    overdue: list[dict[str, Any]] = []
    for item in items:
        first = int(item.get("first_iteration") or 0)
        extensions = int(item.get("extensions") or 0)
        limit = PENDING_ROLL_LIMIT + PENDING_ROLL_LIMIT * extensions
        age = current_iteration - first
        if first and age > limit:
            overdue.append(dict(item))
    return overdue


def assert_run_allowed(state_dir: Path, current_iteration: int) -> None:
    stale = sorted(
        path.name
        for path in Path(state_dir).iterdir()
        if path.is_file() and ".stale-" in path.name
    )
    if stale:
        raise RuntimeError(
            "stale-renamed gate feedback is forbidden; delete the file or "
            "move the issue into pending.json: " + ", ".join(stale)
        )
    pending = load_pending(state_dir)
    overdue = overdue_items(pending.get("items") or [], current_iteration)
    if overdue:
        ids = ", ".join(str(item.get("id")) for item in overdue)
        raise RuntimeError(
            "pending items exceeded the 3-round roll limit; route them back "
            "to Investigate/Solidify or record a human extension: " + ids
        )


def merge_review_into_pending(
    state_dir: Path,
    *,
    iteration: int,
    exclusions: Sequence[Mapping[str, Any]] | None,
    waivers: Sequence[Mapping[str, Any]] | None,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    pending = load_pending(state_dir)
    items = list(pending.get("items") or [])
    live_ids: set[str] = set()
    for item in exclusions or []:
        key = str(item.get("case_key") or "")
        upsert_items(
            items,
            kind="excluded_case",
            key=key,
            reason=str(item.get("reason") or ""),
            route="human",
            iteration=iteration,
        )
        live_ids.add(_item_id("excluded_case", key))
    for item in waivers or []:
        key = str(item.get("criterion_id") or "")
        upsert_items(
            items,
            kind="criterion_waiver",
            key=key,
            reason=str(item.get("reason") or ""),
            route=str(item.get("route") or "solidify"),
            iteration=iteration,
        )
        live_ids.add(_item_id("criterion_waiver", key))
    kept = []
    for item in items:
        if item.get("kind") in {"excluded_case", "criterion_waiver"} and item.get("id") not in live_ids:
            continue
        kept.append(item)
    payload = {"schema_version": PENDING_SCHEMA_VERSION, "items": kept}
    save_pending(state_dir, payload, repository_root=repository_root)
    return payload
