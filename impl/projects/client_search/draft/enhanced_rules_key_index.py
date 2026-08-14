"""enhanced_rules key-index 资产（P4 落地）。

761 条增强规则按 field 切成 106 个可寻址条目；Judge 按 trace 涉及的字段
按键命中（key_live），不再把全量 40 万字符或截断清单注入上下文。

对应 spec/grill/staleness_public_facility.md §3.8：大材料必须检索化。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from impl.core.project_loader import load_project

_RETRIEVE_LIMIT = 20


@lru_cache(maxsize=8)
def _load_enhanced_rules_document(spec_id: str) -> Mapping[str, Any]:
    spec = load_project(spec_id)
    path = Path(spec.source_path("enhanced_rules"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_enhanced_rules_key_index(spec_id: str = "client_search") -> dict[str, list[dict[str, Any]]]:
    """field -> 该字段的规则列表（稳定按键，runtime 拿新的就是）。"""
    doc = _load_enhanced_rules_document(spec_id)
    index: dict[str, list[dict[str, Any]]] = {}
    for rule in doc.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        field = str(rule.get("field") or "").strip()
        if not field:
            continue
        index.setdefault(field, []).append(rule)
    return index


def retrieve_enhanced_rules_for_fields(
    fields: Iterable[str],
    spec_id: str = "client_search",
    limit: int = _RETRIEVE_LIMIT,
) -> dict[str, Any]:
    """按键命中：返回 trace 涉及字段的规则定位键（不是 operator/pattern 正文）。

    merge_to_llm=false 的生成配方不注入。rules 仅含 name/field 定位键；
    negation_words 总是携带（共享小词表）。
    """
    index = build_enhanced_rules_key_index(spec_id)
    wanted = {str(field).strip() for field in fields if str(field).strip()}
    rules: list[dict[str, Any]] = []
    for field in sorted(wanted):
        for rule in index.get(field) or []:
            if not isinstance(rule, dict):
                continue
            if rule.get("merge_to_llm") is False:
                continue
            locator = {
                key: rule[key]
                for key in ("name", "field")
                if key in rule and str(rule.get(key) or "").strip()
            }
            if locator:
                rules.append(locator)
    compact: dict[str, Any] = {}
    if rules:
        compact["rules"] = rules[:limit]
    doc = _load_enhanced_rules_document(spec_id)
    negation = doc.get("negation_words")
    if isinstance(negation, list):
        compact["negation_words"] = negation
    return compact
