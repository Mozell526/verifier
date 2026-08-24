"""In-memory sufficiency overlay.

object_cover / live_identity / wide / surname / role stay as controls.
field_only is the ablation: 1A used as if it fulfilled the whole request.
strip_identity / strip_any are the next rule-table, kept as negative controls.
This file does not import or patch draft/judge.py.
No candidate overlays not_fulfilled.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR_PATH = HERE / "simulate_1a_coverage_program.py"
PRINCIPLE_PATH = HERE / "simulate_1a_principle_program.py"
OUT = HERE / "simulate_1a_sufficiency_program.json"

floor_spec = importlib.util.spec_from_file_location("coverage_floor", FLOOR_PATH)
floor = importlib.util.module_from_spec(floor_spec)
assert floor_spec.loader is not None
floor_spec.loader.exec_module(floor)

principle_spec = importlib.util.spec_from_file_location("object_cover_mod", PRINCIPLE_PATH)
principle = importlib.util.module_from_spec(principle_spec)
assert principle_spec.loader is not None
principle_spec.loader.exec_module(principle)

NAME_FIELDS = floor.NAME_FIELDS
ID_FIELDS = floor.ID_FIELDS
BARE_NAME = floor.BARE_NAME

# Speech wrappers. Negative control only. Not a candidate.
SPEECH_PARTICLES = ("查一下", "有没有", "买过", "买了", "一下", "的")
# Domain leftovers you would add when spreading covering to age/premium/benefit.
DOMAIN_PARTICLES = ("未领取", "以上", "岁", "有", "未")


def load_module_source_sha(*paths: Path) -> dict[str, str]:
    out = {}
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[path.name] = digest
    return out


def name_ok(value: str, catalog: dict[str, set[str]]) -> bool:
    if not BARE_NAME.fullmatch(value):
        return False
    if value in catalog["products"] or value in catalog["addresses"]:
        return False
    return floor.has_surname_shape(value)


def row_pairs(row: dict) -> list[tuple[str, str]] | None:
    fields = [str(item or "") for item in (row.get("fields") or [])]
    values = [str(item).strip() for item in (row.get("values") or [])]
    if len(fields) != len(values):
        return None
    return list(zip(fields, values))


def grounded(query: str, value: str) -> bool:
    return bool(value) and value in query


def field_standard(field: str, value: str, catalog: dict[str, set[str]]) -> str | None:
    """Q1 only. None = this field is out of this mouth's authorization."""
    if field in NAME_FIELDS:
        return "name" if name_ok(value, catalog) else "name_fail"
    if field in ID_FIELDS:
        return "id" if value else "id_fail"
    return None


def decide_field_only(row: dict, catalog: dict[str, set[str]]) -> dict:
    """Ablation: a passing name/id dimension is treated as whole-request success."""
    query = str(row.get("query") or "").strip()
    if query == "":
        return {"status": None, "reason": "empty_query", "hits": []}
    pairs = row_pairs(row)
    if pairs is None:
        return {"status": None, "reason": "pair_ambiguous", "hits": []}
    if not pairs:
        return {"status": None, "reason": "no_live", "hits": []}

    hits = []
    for field, value in pairs:
        if not grounded(query, value):
            continue
        standard = field_standard(field, value, catalog)
        if standard in {"name", "id"}:
            hits.append({"field": field, "value": value, "standard": standard})
    if hits:
        return {"status": "fulfilled", "reason": "field_used_as_request", "hits": hits}
    return {"status": None, "reason": "no_passing_dimension", "hits": []}


def decide_sufficiency(row: dict, catalog: dict[str, set[str]]) -> dict:
    """Authorized mouth: one field, value == whole query, field standard passes."""
    query = str(row.get("query") or "").strip()
    if query == "":
        return {"status": None, "reason": "empty_query", "hits": []}
    pairs = row_pairs(row)
    if pairs is None:
        return {"status": None, "reason": "pair_ambiguous", "hits": []}
    if len(pairs) != 1:
        return {
            "status": None,
            "reason": "not_single_field" if pairs else "no_live",
            "hits": [],
        }
    field, value = pairs[0]
    if value != query:
        return {"status": None, "reason": "value_not_whole_query", "hits": []}
    standard = field_standard(field, value, catalog)
    if standard in {"name", "id"}:
        return {
            "status": "fulfilled",
            "reason": f"sufficient_{standard}",
            "hits": [{"field": field, "value": value, "standard": standard}],
        }
    if standard in {"name_fail", "id_fail"}:
        return {"status": None, "reason": standard, "hits": []}
    return {"status": None, "reason": "field_not_authorized", "hits": []}


def peel(text: str, particles: tuple[str, ...]) -> str:
    leftover = text
    changed = True
    while changed:
        changed = False
        for item in particles:
            if item and item in leftover:
                leftover = leftover.replace(item, "")
                changed = True
    return leftover


def decide_strip(
    row: dict,
    catalog: dict[str, set[str]],
    particles: tuple[str, ...],
    require_identity: bool,
) -> dict:
    """Negative control: covering after peeling a particle table."""
    query = str(row.get("query") or "").strip()
    if query == "":
        return {"status": None, "reason": "empty_query", "residual": ""}
    pairs = row_pairs(row)
    if pairs is None:
        return {"status": None, "reason": "pair_ambiguous", "residual": query}
    if not pairs:
        return {"status": None, "reason": "no_live", "residual": query}

    spans, ground_reason = principle.ground_spans(query, pairs)
    if spans is None:
        return {"status": None, "reason": ground_reason, "residual": query}
    residual = principle.leftover_text(query, spans)
    peeled = peel(residual, particles)
    if re.sub(r"\s+", "", peeled) != "":
        return {"status": None, "reason": "residual_after_strip", "residual": peeled}

    kinds = [principle.field_kind(field) for field, _value in pairs]
    if require_identity and not any(kind in {"name", "id"} for kind in kinds):
        return {"status": None, "reason": "no_identity_field", "residual": ""}
    for field, value in pairs:
        kind = principle.field_kind(field)
        if kind == "name" and not name_ok(value, catalog):
            return {"status": None, "reason": "name_not_ok", "residual": ""}
        if require_identity and kind == "other":
            return {"status": None, "reason": "other_field", "residual": ""}
    return {"status": "fulfilled", "reason": "strip_cover", "residual": ""}


def exit_field_only(row: dict, catalog: dict[str, set[str]]) -> str | None:
    decision = decide_field_only(row, catalog)
    row["field_only_reason"] = decision["reason"]
    row["field_only_hits"] = decision["hits"]
    return decision["status"]


def exit_sufficiency(row: dict, catalog: dict[str, set[str]]) -> str | None:
    decision = decide_sufficiency(row, catalog)
    row["sufficiency_reason"] = decision["reason"]
    row["sufficiency_hits"] = decision["hits"]
    return decision["status"]


def exit_strip_identity(row: dict, catalog: dict[str, set[str]]) -> str | None:
    decision = decide_strip(row, catalog, SPEECH_PARTICLES, require_identity=True)
    row["strip_identity_reason"] = decision["reason"]
    row["strip_identity_residual"] = decision.get("residual", "")
    return decision["status"]


def exit_strip_any(row: dict, catalog: dict[str, set[str]]) -> str | None:
    decision = decide_strip(
        row,
        catalog,
        SPEECH_PARTICLES + DOMAIN_PARTICLES,
        require_identity=False,
    )
    row["strip_any_reason"] = decision["reason"]
    row["strip_any_residual"] = decision.get("residual", "")
    return decision["status"]


def synthetic_rows() -> list[dict]:
    return [
        {
            "id": "SYN-yangjie",
            "query": "杨杰",
            "fields": ["searchClientName"],
            "values": ["杨杰"],
            "expect_sufficiency": "fulfilled",
            "expect_field_only": "fulfilled",
            "why": "bare name, 1A passes, sufficiency fires",
        },
        {
            "id": "SYN-wang",
            "query": "王坤林",
            "fields": ["searchClientName"],
            "values": ["王坤林"],
            "expect_sufficiency": "fulfilled",
            "expect_field_only": "fulfilled",
            "why": "same side as 杨杰",
        },
        {
            "id": "SYN-gongzhan",
            "query": "共展",
            "fields": ["searchClientName"],
            "values": ["共展"],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "no surname; inherit, never overlay NF",
        },
        {
            "id": "SYN-haoxuan",
            "query": "昊轩",
            "fields": ["searchClientName"],
            "values": ["昊轩"],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "parked two-char given name",
        },
        {
            "id": "SYN-honglian",
            "query": "红莲保单",
            "fields": ["searchClientName"],
            "values": ["红莲"],
            "expect_sufficiency": None,
            "expect_field_only": "fulfilled",
            "why": "ablation: field_only lifts a policy request because a name passed 1A",
        },
        {
            "id": "SYN-survival",
            "query": "唐诗颖的生存金有没有领取",
            "fields": ["searchClientName"],
            "values": ["唐诗颖"],
            "expect_sufficiency": None,
            "expect_field_only": "fulfilled",
            "why": "diffusion: name dimension is not the request",
        },
        {
            "id": "SYN-zhang-policy",
            "query": "张忠波保单号",
            "fields": ["searchClientName"],
            "values": ["张忠波"],
            "expect_sufficiency": None,
            "expect_field_only": "fulfilled",
            "why": "field_only would speak; sufficiency must keep current F by inheriting",
        },
        {
            "id": "SYN-lookup",
            "query": "查一下李明",
            "fields": ["searchClientName"],
            "values": ["李明"],
            "expect_sufficiency": None,
            "expect_field_only": "fulfilled",
            "why": "speech wrapper is not a sufficiency hit; peeling it is the next table",
        },
        {
            "id": "SYN-particle",
            "query": "李明的重疾险",
            "fields": ["searchClientName", "polNoInfo.plancodeinfo.abbrname"],
            "values": ["李明", "重疾险"],
            "expect_sufficiency": None,
            "expect_field_only": "fulfilled",
            "why": "both objects delivered; sufficiency still abstains; strip would need 的",
        },
        {
            "id": "SYN-concat",
            "query": "李明重疾险",
            "fields": ["searchClientName", "polNoInfo.plancodeinfo.abbrname"],
            "values": ["李明", "重疾险"],
            "expect_sufficiency": None,
            "expect_field_only": "fulfilled",
            "why": "object_cover would overlay; this mouth must not",
        },
        {
            "id": "SYN-dropped",
            "query": "李明的重疾险",
            "fields": ["polNoInfo.plancodeinfo.abbrname"],
            "values": ["重疾险"],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "parser dropped the name; do not invent 李明",
        },
        {
            "id": "SYN-empty",
            "query": "家办客户",
            "fields": [],
            "values": [],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "empty live cannot invent success",
        },
        {
            "id": "SYN-age",
            "query": "45岁女性保费10万以上",
            "fields": ["clientAge", "clientSex", "annPremSegNum"],
            "values": ["45", "女性", "10万"],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "non-name request; covering needs new field kinds + 岁/以上 table",
        },
        {
            "id": "SYN-benefit",
            "query": "有生存金未领取",
            "fields": ["polNoInfo.payamountdue"],
            "values": ["是"],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "value is not in the query; no authorized mouth",
        },
        {
            "id": "SYN-jinfeng-name",
            "query": "金凤",
            "fields": ["searchClientName"],
            "values": ["金凤"],
            "expect_sufficiency": None,
            "expect_field_only": None,
            "why": "catalog product must not take the name exit",
        },
    ]


def run_synthetics(catalog: dict[str, set[str]]) -> dict:
    rows = []
    for item in synthetic_rows():
        suf = decide_sufficiency(item, catalog)
        field = decide_field_only(item, catalog)
        cover = principle.decide_object_cover(item, catalog)
        identity = floor.exit_live_identity(item, catalog)
        strip_i = decide_strip(item, catalog, SPEECH_PARTICLES, True)
        strip_a = decide_strip(item, catalog, SPEECH_PARTICLES + DOMAIN_PARTICLES, False)
        ok = suf["status"] == item["expect_sufficiency"] and field["status"] == item["expect_field_only"]
        rows.append(
            {
                "id": item["id"],
                "query": item["query"],
                "fields": item["fields"],
                "values": item["values"],
                "why": item["why"],
                "sufficiency": suf["status"],
                "sufficiency_reason": suf["reason"],
                "field_only": field["status"],
                "field_only_reason": field["reason"],
                "object_cover": cover["status"],
                "object_cover_reason": cover["reason"],
                "live_identity": identity,
                "strip_identity": strip_i["status"],
                "strip_any": strip_a["status"],
                "expect_sufficiency": item["expect_sufficiency"],
                "expect_field_only": item["expect_field_only"],
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
                "current": row.get("current"),
                left: row.get(left),
                f"{left}_mode": row.get(f"{left}_mode"),
                right: row.get(right),
                f"{right}_mode": row.get(f"{right}_mode"),
                "left_reason": row.get(f"{left}_reason"),
                "right_reason": row.get(f"{right}_reason"),
            }
        )
    return out


def compact_score(val: dict) -> dict:
    return {
        "n_labeled": val.get("n_labeled"),
        "tested": val.get("tested"),
        "agree": val.get("agree"),
        "disagree": val.get("disagree"),
        "by_role": val.get("by_role"),
    }


def main() -> None:
    set_a = floor.load_set_a()
    collected = floor.load_collected()
    mixed = floor.load_mixed_rows(set_a, collected)
    catalog = floor.build_catalog(set_a)

    exits = {
        "wide": floor.exit_wide,
        "surname": floor.exit_surname,
        "role": floor.exit_role,
        "live_identity": floor.exit_live_identity,
        "object_cover": principle.exit_object_cover,
        "field_only": exit_field_only,
        "sufficiency": exit_sufficiency,
        "strip_identity": exit_strip_identity,
        "strip_any": exit_strip_any,
    }
    floor.annotate(set_a, catalog, exits)
    floor.annotate(mixed, catalog, exits)
    synthetics = run_synthetics(catalog)

    mixed_scores = {name: compact_score(floor.score_pack(mixed, name)) for name in ["current", *exits]}

    payload = {
        "note": (
            "sufficiency is the candidate mouth. field_only is the ablation. "
            "object_cover / live_identity / strip_* are controls. "
            "No function is merged into draft/judge.py."
        ),
        "source_sha256": load_module_source_sha(
            Path(__file__), FLOOR_PATH, PRINCIPLE_PATH
        ),
        "catalog_projection": {
            "n_products": len(catalog["products"]),
            "n_addresses": len(catalog["addresses"]),
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
            "sufficiency_vs_live_identity": diff_rows(set_a, "live_identity", "sufficiency"),
            "sufficiency_vs_object_cover": diff_rows(set_a, "object_cover", "sufficiency"),
            "field_only_vs_sufficiency": diff_rows(set_a, "sufficiency", "field_only"),
            "reason_counts": {
                "sufficiency": dict(Counter(row.get("sufficiency_reason") for row in set_a)),
                "field_only": dict(Counter(row.get("field_only_reason") for row in set_a)),
            },
        },
        "mixed": {
            "n": len(mixed),
            "current_sources": dict(Counter(row["current_source"] for row in mixed)),
            "scores": mixed_scores,
            "modes": {name: floor.mode_report(mixed, name) for name in exits},
            "business_cells": {
                name: floor.business_cells(mixed, name) for name in ["current", *exits]
            },
            "sufficiency_vs_live_identity": diff_rows(mixed, "live_identity", "sufficiency"),
            "sufficiency_vs_object_cover": diff_rows(mixed, "object_cover", "sufficiency"),
            "field_only_vs_sufficiency": diff_rows(mixed, "sufficiency", "field_only"),
            "reason_counts": {
                "sufficiency": dict(Counter(row.get("sufficiency_reason") for row in mixed)),
                "field_only": dict(Counter(row.get("field_only_reason") for row in mixed)),
            },
        },
        "set_b_file": str(floor.HERE / "head_set_b.json") if hasattr(floor, "HERE") else None,
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    payload["dump_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "out": str(OUT),
        "dump_sha256": payload["dump_sha256"],
        "synthetics_ok": synthetics["all_ok"],
        "failed_ids": synthetics["failed_ids"],
        "mixed_agree": {k: v.get("agree") for k, v in mixed_scores.items()},
        "set_a_field_only_extra": len(payload["set_a"]["field_only_vs_sufficiency"]),
        "set_a_suf_vs_identity": len(payload["set_a"]["sufficiency_vs_live_identity"]),
        "set_a_suf_vs_cover": len(payload["set_a"]["sufficiency_vs_object_cover"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
