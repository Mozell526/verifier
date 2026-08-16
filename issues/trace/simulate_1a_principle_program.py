"""In-memory object-cover overlay.

live_identity / wide / surname / role stay as negative controls.
This file does not import or patch draft/judge.py.
object_cover never overlays not_fulfilled.
"""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR_PATH = HERE / "simulate_1a_coverage_program.py"
OUT = HERE / "simulate_1a_principle_program.json"

spec = importlib.util.spec_from_file_location("coverage_floor", FLOOR_PATH)
floor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(floor)

NAME_FIELDS = floor.NAME_FIELDS
ID_FIELDS = floor.ID_FIELDS
CATALOG_FIELDS = floor.CATALOG_FIELDS
BARE_NAME = floor.BARE_NAME


def field_kind(field: str) -> str:
    if field in NAME_FIELDS:
        return "name"
    if field in ID_FIELDS:
        return "id"
    if field in CATALOG_FIELDS:
        return "catalog"
    return "other"


def row_pairs(row: dict) -> list[tuple[str, str]] | None:
    """Align (field, value) without inventing pairs.

    Length mismatch means the flattened live dump is ambiguous → inherit.
    """
    fields = [str(item or "") for item in (row.get("fields") or [])]
    values = [str(item).strip() for item in (row.get("values") or [])]
    if len(fields) != len(values):
        return None
    return list(zip(fields, values))


def ground_spans(query: str, pairs: list[tuple[str, str]]) -> tuple[list[tuple[int, int]] | None, str]:
    occupied = [False] * len(query)
    spans: list[tuple[int, int]] = []
    for _field, value in pairs:
        if value == "":
            return None, "value_empty"
        start = 0
        found: tuple[int, int] | None = None
        while True:
            idx = query.find(value, start)
            if idx < 0:
                return None, "not_grounded"
            end = idx + len(value)
            if not any(occupied[idx:end]):
                found = (idx, end)
                break
            start = idx + 1
        assert found is not None
        for pos in range(found[0], found[1]):
            occupied[pos] = True
        spans.append(found)
    return spans, "grounded"


def leftover_text(query: str, spans: list[tuple[int, int]]) -> str:
    occupied = [False] * len(query)
    for start, end in spans:
        for pos in range(start, end):
            occupied[pos] = True
    return "".join(char for char, used in zip(query, occupied) if not used)


def name_object_ok(value: str, catalog: dict[str, set[str]]) -> bool:
    if not BARE_NAME.fullmatch(value):
        return False
    if value in catalog["products"] or value in catalog["addresses"]:
        return False
    return floor.has_surname_shape(value)


def decide_object_cover(row: dict, catalog: dict[str, set[str]]) -> dict:
    query = str(row.get("query") or "").strip()
    if query == "":
        return {"status": None, "reason": "empty_query", "residual": "", "pairs": []}

    pairs = row_pairs(row)
    if pairs is None:
        return {"status": None, "reason": "pair_ambiguous", "residual": query, "pairs": []}
    if not pairs:
        return {"status": None, "reason": "no_live", "residual": query, "pairs": []}

    spans, ground_reason = ground_spans(query, pairs)
    if spans is None:
        return {"status": None, "reason": ground_reason, "residual": query, "pairs": pairs}

    residual = leftover_text(query, spans)
    if residual.strip() != "":
        return {
            "status": None,
            "reason": "residual_nonempty",
            "residual": residual,
            "pairs": pairs,
        }

    kinds = [field_kind(field) for field, _value in pairs]
    if not any(kind in {"name", "id"} for kind in kinds):
        return {
            "status": None,
            "reason": "no_identity_field",
            "residual": "",
            "pairs": pairs,
        }

    for field, value in pairs:
        kind = field_kind(field)
        if kind == "name" and not name_object_ok(value, catalog):
            return {
                "status": None,
                "reason": "name_not_ok",
                "residual": "",
                "pairs": pairs,
            }
        if kind == "other":
            return {
                "status": None,
                "reason": "other_field",
                "residual": "",
                "pairs": pairs,
            }

    if any(kind == "name" for kind in kinds):
        reason = "overlay_f_mixed" if any(kind != "name" for kind in kinds) else "overlay_f_name"
    else:
        reason = "overlay_f_id"
    return {"status": "fulfilled", "reason": reason, "residual": "", "pairs": pairs}


def exit_object_cover(row: dict, catalog: dict[str, set[str]]) -> str | None:
    decision = decide_object_cover(row, catalog)
    row["object_cover_reason"] = decision["reason"]
    row["object_cover_residual"] = decision["residual"]
    return decision["status"]


def synthetic_rows() -> list[dict]:
    return [
        {
            "id": "SYN-yangjie",
            "query": "杨杰",
            "fields": ["searchClientName"],
            "values": ["杨杰"],
            "expect_status": "fulfilled",
            "expect_mode": "overlay",
            "why": "single name, residual empty, 1A prior hits",
        },
        {
            "id": "SYN-gongzhan",
            "query": "共展",
            "fields": ["searchClientName"],
            "values": ["共展"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "empty residual but no surname; must inherit, not overlay NF",
        },
        {
            "id": "SYN-haoxuan",
            "query": "昊轩",
            "fields": ["searchClientName"],
            "values": ["昊轩"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "parked 1A policy; no surname → inherit",
        },
        {
            "id": "SYN-honglian",
            "query": "红莲保单",
            "fields": ["searchClientName"],
            "values": ["红莲"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "residual 保单; question-shape must not lift F",
        },
        {
            "id": "SYN-zhang-policy",
            "query": "张忠波保单号",
            "fields": ["searchClientName"],
            "values": ["张忠波"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "residual 保单号; must not kill current F",
        },
        {
            "id": "SYN-lookup-liming",
            "query": "查一下李明",
            "fields": ["searchClientName"],
            "values": ["李明"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "residual 查一下; do not strip speech wrappers",
        },
        {
            "id": "SYN-concat-name-product",
            "query": "李明重疾险",
            "fields": ["searchClientName", "polNoInfo.plancodeinfo.abbrname"],
            "values": ["李明", "重疾险"],
            "expect_status": "fulfilled",
            "expect_mode": "overlay",
            "why": "true extra vs whole-query gate: two objects, residual empty",
        },
        {
            "id": "SYN-particle-name-product",
            "query": "李明的重疾险",
            "fields": ["searchClientName", "polNoInfo.plancodeinfo.abbrname"],
            "values": ["李明", "重疾险"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "residual 的; peeling 的 would be the next rule table",
        },
        {
            "id": "SYN-name-product-dropped",
            "query": "李明的重疾险",
            "fields": ["polNoInfo.plancodeinfo.abbrname"],
            "values": ["重疾险"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "parser dropped the name; do not invent 李明 from the query",
        },
        {
            "id": "SYN-zongtuo",
            "query": "综拓潜客",
            "fields": ["validSinsPol", "pajjMemberGradeInfo.pajjmemberstatus"],
            "values": ["综拓", "潜客"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "I129 real boundary: empty residual but no identity field",
        },
        {
            "id": "SYN-empty-live",
            "query": "家办客户",
            "fields": [],
            "values": [],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "empty live cannot invent success from the query",
        },
        {
            "id": "SYN-two-ids",
            "query": "C000888123456P01000008888888",
            "fields": ["clientNo", "polNo"],
            "values": ["C000888123456", "P01000008888888"],
            "expect_status": "fulfilled",
            "expect_mode": "overlay",
            "why": "two IDs covering the whole query; whole-query gate cannot fire",
        },
        {
            "id": "SYN-id-wrapper",
            "query": "找一下客户号C000777123456",
            "fields": ["clientNo"],
            "values": ["C000777123456"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "HB018 shape: value is not the whole query",
        },
        {
            "id": "SYN-jinfeng-name",
            "query": "金凤",
            "fields": ["searchClientName"],
            "values": ["金凤"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "catalog product must not take the name exit",
        },
        {
            "id": "SYN-jinfeng-product",
            "query": "金凤",
            "fields": ["polNoInfo.plancodeinfo.abbrname"],
            "values": ["金凤"],
            "expect_status": None,
            "expect_mode": "inherit",
            "why": "catalog-only, even with empty residual, is out of scope",
        },
    ]


def run_synthetics(catalog: dict[str, set[str]]) -> dict:
    rows = []
    for item in synthetic_rows():
        cover = decide_object_cover(item, catalog)
        identity = floor.exit_live_identity(item, catalog)
        status, mode = floor.apply_exit({"current": None}, cover["status"])
        identity_status, identity_mode = floor.apply_exit({"current": None}, identity)
        ok = mode == item["expect_mode"] and (
            (item["expect_status"] is None and cover["status"] is None)
            or cover["status"] == item["expect_status"]
        )
        rows.append(
            {
                "id": item["id"],
                "query": item["query"],
                "fields": item["fields"],
                "values": item["values"],
                "why": item["why"],
                "object_cover": cover["status"],
                "object_cover_mode": mode,
                "object_cover_reason": cover["reason"],
                "object_cover_residual": cover["residual"],
                "live_identity": identity,
                "live_identity_mode": identity_mode,
                "expect_status": item["expect_status"],
                "expect_mode": item["expect_mode"],
                "probe_ok": ok,
            }
        )
    return {
        "n": len(rows),
        "all_ok": all(row["probe_ok"] for row in rows),
        "failed_ids": [row["id"] for row in rows if not row["probe_ok"]],
        "rows": rows,
    }


def diff_rows(rows: list[dict], left: str, right: str) -> list[dict]:
    out = []
    for row in rows:
        if row.get(left) == row.get(right) and row.get(f"{left}_mode") == row.get(f"{right}_mode"):
            continue
        out.append(
            {
                "id": row.get("id"),
                "query": row.get("query"),
                "fields": row.get("fields"),
                "values": row.get("values"),
                left: row.get(left),
                f"{left}_mode": row.get(f"{left}_mode"),
                right: row.get(right),
                f"{right}_mode": row.get(f"{right}_mode"),
                "reason": row.get(f"{right}_reason") or row.get("object_cover_reason"),
                "residual": row.get("object_cover_residual"),
            }
        )
    return out


def compact_score(val: dict) -> dict:
    return {
        "tested": val["tested"],
        "agree": val["agree"],
        "disagree": val["disagree"],
        "untested": val["untested"],
        "misses": [
            item["id"] + ":" + str(item["got"]) + "/" + str(item.get("mode"))
            for item in val["misses"]
        ],
    }


def source_len() -> dict:
    return {
        **floor.source_len(),
        "exit_object_cover": len(inspect.getsource(exit_object_cover).splitlines()),
        "decide_object_cover": len(inspect.getsource(decide_object_cover).splitlines()),
    }


def main() -> None:
    set_a = floor.load_set_a()
    catalog = floor.build_catalog(set_a)
    collected = floor.load_collected()
    mixed = floor.load_mixed_rows(set_a, collected)
    exits = {
        "wide": floor.exit_wide,
        "surname": floor.exit_surname,
        "role": floor.exit_role,
        "live_identity": floor.exit_live_identity,
        "object_cover": exit_object_cover,
    }
    floor.annotate(set_a, catalog, exits)
    floor.annotate(mixed, catalog, exits)

    mixed_scores = {name: floor.score_pack(mixed, name) for name in ["current", *exits]}
    synthetics = run_synthetics(catalog)
    payload = {
        "note": (
            "Object-cover experiment. current=fresh judge or xlsx. "
            "wide/surname/role/live_identity are negative controls. "
            "object_cover is the only candidate. "
            "live_identity is the single-field whole-query special case, not the architecture. "
            "Mixed-pack agree is not a KPI. "
            "If frozen scores match live_identity, this round wins on bounds, not on a new number."
        ),
        "source_lines": source_len(),
        "catalog_projection": {
            "n_products": len(catalog["products"]),
            "products": sorted(catalog["products"]),
        },
        "live_facts": floor.live_facts(mixed),
        "synthetics": synthetics,
        "set_a": {
            "n": len(set_a),
            "current": dict(Counter(row["current"] for row in set_a)),
            **{name: dict(Counter(row[name] for row in set_a)) for name in exits},
            "gates": {name: floor.gate_set_a(set_a, name) for name in ["current", *exits]},
            "flips": {name: floor.set_a_flips(set_a, name) for name in exits},
            "modes": {name: floor.mode_report(set_a, name) for name in exits},
            "object_cover_vs_live_identity": diff_rows(set_a, "live_identity", "object_cover"),
            "reason_counts": dict(Counter(row.get("object_cover_reason") for row in set_a)),
        },
        "mixed": {
            "n": len(mixed),
            "current_sources": dict(Counter(row["current_source"] for row in mixed)),
            "scores": mixed_scores,
            "modes": {name: floor.mode_report(mixed, name) for name in exits},
            "business_cells": {
                name: floor.business_cells(mixed, name) for name in ["current", *exits]
            },
            "object_cover_vs_live_identity": diff_rows(mixed, "live_identity", "object_cover"),
            "reason_counts": dict(Counter(row.get("object_cover_reason") for row in mixed)),
            "rows": [
                {
                    "id": row["id"],
                    "query": row["query"],
                    "pack_role": row["pack_role"],
                    "expected": row["expected"],
                    "fields": row["fields"],
                    "values": row["values"],
                    "current": row["current"],
                    "current_source": row["current_source"],
                    "wide": row["wide"],
                    "wide_mode": row["wide_mode"],
                    "surname": row["surname"],
                    "surname_mode": row["surname_mode"],
                    "role": row["role"],
                    "role_mode": row["role_mode"],
                    "live_identity": row["live_identity"],
                    "live_identity_mode": row["live_identity_mode"],
                    "object_cover": row["object_cover"],
                    "object_cover_mode": row["object_cover_mode"],
                    "object_cover_reason": row.get("object_cover_reason"),
                    "object_cover_residual": row.get("object_cover_residual"),
                }
                for row in mixed
            ],
        },
        "set_b_file": {
            "path": str(floor.SET_B),
            "n": len(json.loads(floor.SET_B.read_text(encoding="utf-8"))["cases"]),
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "sha256": digest,
                "source_lines": payload["source_lines"],
                "synthetics_all_ok": synthetics["all_ok"],
                "synthetics_failed": synthetics["failed_ids"],
                "set_a_counts": {
                    "current": payload["set_a"]["current"],
                    **{name: payload["set_a"][name] for name in exits},
                },
                "set_a_flip_n": {
                    name: {
                        "lifted": len(payload["set_a"]["flips"][name]["lifted_to_f"]),
                        "dropped": len(payload["set_a"]["flips"][name]["dropped_to_nf"]),
                        "lifted_ids": [
                            item["id"] + ":" + item["query"]
                            for item in payload["set_a"]["flips"][name]["lifted_to_f"]
                        ],
                        "dropped_ids": [
                            item["id"] + ":" + item["query"]
                            for item in payload["set_a"]["flips"][name]["dropped_to_nf"]
                        ],
                    }
                    for name in exits
                },
                "set_a_diff_vs_live_identity": payload["set_a"]["object_cover_vs_live_identity"],
                "mixed_scores": {name: compact_score(mixed_scores[name]) for name in mixed_scores},
                "mixed_modes": {
                    name: {
                        "overlay_n": payload["mixed"]["modes"][name]["overlay_n"],
                        "inherit_n": payload["mixed"]["modes"][name]["inherit_n"],
                        "overlay_ids": payload["mixed"]["modes"][name]["overlay_ids"],
                    }
                    for name in exits
                },
                "mixed_diff_vs_live_identity": payload["mixed"]["object_cover_vs_live_identity"],
                "mixed_reasons": payload["mixed"]["reason_counts"],
                "set_a_reasons": payload["set_a"]["reason_counts"],
                "mixed_business": payload["mixed"]["business_cells"]["object_cover"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
