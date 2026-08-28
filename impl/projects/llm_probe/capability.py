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


def capability_service(ref: str) -> dict[str, Any]:
    """capability 预设自带的探测端点配置（url/method/timeout_seconds）。"""
    entry = load_capability_map().get(ref)
    service = entry.get("service") if isinstance(entry, dict) else None
    if not isinstance(service, dict) or not str(service.get("url") or "").strip():
        raise ValueError(f"capability_map.yaml 没有 {ref} 的 service.url 配置")
    return service


def default_capability_ref() -> str:
    mapping = load_capability_map()
    # 按 key 排序取默认项，避免依赖 YAML 键的书写顺序。
    for key in sorted(mapping):
        if capability_text(mapping[key]):
            return str(key)
    raise ValueError("capability_map.yaml 为空")


def _fill_template(value: Any, query: str) -> Any:
    if isinstance(value, str):
        return value.replace("{query}", query)
    if isinstance(value, dict):
        return {key: _fill_template(item, query) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill_template(item, query) for item in value]
    return value


def mock_body(ref: str, query: str) -> dict[str, Any]:
    """按 capability_map 中的 mock_body 模板生成目标项目可接受的请求 body。"""
    entry = load_capability_map().get(ref)
    template = entry.get("mock_body") if isinstance(entry, dict) else None
    if not isinstance(template, dict):
        raise ValueError(f"capability_map.yaml 没有 {ref} 的 mock_body 模板")
    return _fill_template(template, query)
