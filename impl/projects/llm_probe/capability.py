from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_MAP_PATH = Path(__file__).with_name("capability_map.yaml")


def load_capability_map() -> dict[str, Any]:
    data = yaml.safe_load(_MAP_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("capability_map.yaml must be a mapping of project_id -> capability")
    return data


def capability_text(entry: Any) -> str:
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        return str(entry.get("capability") or "").strip()
    return ""


def resolve_capability(request: dict[str, Any]) -> str:
    explicit = str(request.get("capability") or "").strip()
    if explicit:
        return explicit
    ref = str(request.get("capability_ref") or "").strip()
    if not ref:
        raise ValueError("llm_probe request 需要 capability 或 capability_ref")
    text = capability_text(load_capability_map().get(ref))
    if not text:
        raise ValueError(f"capability_map.yaml 没有 {ref} 的能力描述")
    return text


def default_capability_ref() -> str:
    mapping = load_capability_map()
    for key, entry in mapping.items():
        if capability_text(entry):
            return str(key)
    raise ValueError("capability_map.yaml 为空")
