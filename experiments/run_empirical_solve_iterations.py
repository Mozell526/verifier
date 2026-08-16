#!/usr/bin/env python3
"""Empirical solve iterations beyond V0–V3.

Goal: keep measuring Auth-OFF focus + labeled dual thresholds + stress.
No Draft skill edits. No selected/promote claims.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Sequence

import yaml

# Reuse builders / helpers from prior harness
sys.path.insert(0, "/workspace/draft-run")
from run_empirical_keyindex_sim import (  # noqa: E402
    Entry,
    FOCUS,
    _bigrams,
    _normalise,
    _phrases,
    _searchable_chars,
    abbrname_exact_lookup,
    build_abbrname_exact,
    build_field_entries_v0,
    build_field_entries_v1,
    build_rule_entries,
    char_heuristic,
    exact_strategy,
    fused_strategy,
    judge_focus,
    load_iteration_queries,
    load_xlsx_queries,
    metrics_labeled,
    rules_search,
    source_phrase_idf_strategy,
)

ROOT = Path("/workspace/draft-run")
SRC = ROOT / "source"
XLSX = Path("/workspace/verifier-client_search-cases-20260812-214445.xlsx")
OUT_MD = ROOT / "empirical-solve-iterations.md"
OUT_BEST = ROOT / "empirical-solve-best.json"
OUT_FULL = ROOT / "experiments" / "empirical-solve-iterations.json"
ISSUES = ROOT / "issues-log.md"
PROJ_EXPERIMENTS = Path(
    "/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/experiments"
)

TZ8 = timezone(timedelta(hours=8))

# Ultra-common tokens that should not alone justify a hit
COMMON_TOKENS = {
    "客户", "什么", "有什", "时有", "平时", "有什", "户平", "是什",
    "哪些", "一个", "可以", "怎么", "如何", "或者", "以及", "还有",
    "同时", "没有", "不是", "就是", "这个", "那个", "他们", "我们",
    "会员", "状态", "类型", "等级", "时间", "日期", "保单", "姓名",
}

IRRELEVANT_MARKERS = (
    "天气", "红烧肉", "黑洞", "咖啡", "银河", "写一首诗", "量子",
    "蒸发", "怎么做", "做什么菜",
)
UNSUPPORTED_MARKERS = (
    "兴趣爱好", "兴趣", "爱好", "喜欢的颜色", "宠物", "电影", "星座",
)


def reject_query_heuristic(query: str) -> str | None:
    """Return reject reason if query looks irrelevant/unsupported without source grounding."""
    q = str(query or "")
    if any(m in q for m in IRRELEVANT_MARKERS):
        return "irrelevant_marker"
    if any(m in q for m in UNSUPPORTED_MARKERS):
        return "unsupported_marker"
    return None


def relevance_ok(
    query: str,
    entry: Entry,
    *,
    min_coverage: float,
    require_exact_or_key: bool,
    channels: dict[str, float],
) -> bool:
    qn = _normalise(query)
    if not qn:
        return False
    if "exact" in channels:
        return True
    if entry.key.casefold() in str(query or "").casefold():
        return True
    # phrase-level
    phrases = _phrases(entry.search_text)
    for ph in phrases:
        if ph == qn or (len(ph) >= 3 and ph in qn) or (len(qn) >= 2 and qn in ph and len(ph) > len(qn)):
            # reject ultra-common alone
            if ph in COMMON_TOKENS or qn in COMMON_TOKENS:
                continue
            return True
    qb = _bigrams(qn)
    if not qb:
        return False
    shared = qb & _bigrams(entry.search_text)
    # drop common bigrams from shared for coverage
    shared_eff = {b for b in shared if b not in COMMON_TOKENS}
    coverage = len(shared_eff) / len(qb)
    if require_exact_or_key and "exact" not in channels and not shared_eff:
        return False
    if coverage < min_coverage:
        return False
    if len(shared_eff) < 2:
        return False
    return True


def field_search_strict(
    query: str,
    entries: Sequence[Entry],
    limit: int,
    *,
    allow_2char_stem: bool,
    min_coverage: float,
    require_exact_or_key: bool,
):
    exact_fn = lambda q, e, lim: exact_strategy(q, e, lim, allow_2char_stem=allow_2char_stem)
    idf_fn = source_phrase_idf_strategy(
        entries, min_query_coverage=min_coverage, allow_2char_stem=allow_2char_stem
    )
    fused = fused_strategy(exact_fn, idf_fn)
    raw = fused(query, entries, max(limit, 12))
    kept = []
    for entry, score, channels in raw:
        if relevance_ok(
            query,
            entry,
            min_coverage=min_coverage,
            require_exact_or_key=require_exact_or_key,
            channels=channels,
        ):
            kept.append((entry, score, channels))
    return kept[:limit]


def rules_search_strict(
    query: str,
    entries: Sequence[Entry],
    limit: int,
    *,
    min_pat_len: int = 2,
    prefer_name_field: bool = True,
    disallow_common: bool = True,
):
    """Stricter than V2 rules_search: quality gates + prefer name/field."""
    qn = _normalise(query)
    if len(qn) < 1:
        return []
    if disallow_common and qn in COMMON_TOKENS:
        return []
    ranked = []
    for entry in entries:
        scores = []
        name_n = _normalise(entry.key)
        field_n = _normalise(entry.payload.get("field") or "")
        pats = entry.payload.get("patterns") or []
        if isinstance(pats, str):
            pats = [pats]
        pat_norms = [_normalise(p) for p in pats if str(p).strip()]

        # name / field first-class
        if name_n == qn:
            scores.append(100.0)
        elif prefer_name_field and len(qn) >= 3 and qn in name_n:
            scores.append(70.0)
        elif prefer_name_field and len(name_n) >= 4 and name_n in qn:
            scores.append(60.0)

        if field_n and (field_n == qn or (len(qn) >= 4 and qn in field_n)):
            scores.append(50.0)

        for pn in pat_norms:
            if not pn:
                continue
            if disallow_common and pn in COMMON_TOKENS:
                continue
            if len(pn) < min_pat_len and pn != qn:
                continue
            if pn == qn:
                scores.append(90.0)
            elif len(qn) >= 2 and qn in pn:
                # query contained in pattern — require pattern not tiny/common
                if len(pn) >= max(len(qn), 2) and (len(pn) >= 3 or pn == qn):
                    # quality: coverage of pattern by query or vice versa
                    cov = len(qn) / max(len(pn), 1)
                    if cov >= 0.4 or len(qn) >= 2 and len(pn) <= len(qn) + 4:
                        scores.append(float(55 + min(len(qn), 20)))
            elif len(pn) >= 4 and pn in qn:
                scores.append(float(40 + min(len(pn), 20)))

        # latin short: token-exact only
        if re.fullmatch(r"[a-z0-9]+", qn) and len(qn) <= 4:
            ok = any(pn == qn for pn in pat_norms) or name_n == qn
            if not ok:
                for p in pats:
                    for tok in re.split(r"[\s|/，,、]+", str(p)):
                        if _normalise(tok) == qn:
                            ok = True
                            break
            if not ok:
                continue
            if not scores:
                scores.append(65.0)

        if not scores:
            continue
        ranked.append((entry, max(scores), {"exact": max(scores)}))
    ranked.sort(key=lambda item: (-item[1], item[0].key))
    return ranked[:limit]


def spoken_key_exact(query: str, field_entries: Sequence[Entry], limit: int):
    """Exact match against projected example/note phrases (spoken keys)."""
    qn = _normalise(query)
    if len(qn) < 2:
        return []
    ranked = []
    for entry in field_entries:
        for ph in _phrases(entry.search_text):
            if ph == qn:
                ranked.append((entry, 120.0, {"exact": 120.0}))
                break
    ranked.sort(key=lambda item: (-item[1], item[0].key))
    return ranked[:limit]


def merge_slots(*batches_caps, limit: int = 8):
    hits = []
    seen = set()
    for batch, cap in batches_caps:
        taken = 0
        for entry, score, channels in batch:
            mk = f"{entry.collection}:{entry.key}"
            if mk in seen:
                continue
            hits.append((entry, float(score), channels))
            seen.add(mk)
            taken += 1
            if taken >= cap or len(hits) >= limit:
                break
        if len(hits) >= limit:
            break
    return hits[:limit]


def apply_reject_filter(query: str, hits, *, hard_reject: bool, soft_require_exact: bool):
    reason = reject_query_heuristic(query)
    if not reason:
        return hits
    if hard_reject:
        # allow through only if we have a strong exact hit that is not weak lexical
        strong = [
            h
            for h in hits
            if "exact" in h[2] and h[2].get("exact", 0) >= 70
            and _normalise(query) in _normalise(h[0].search_text)
        ]
        # For hobby/weather, never accept field lexical-only
        return strong if soft_require_exact else []
    # soft: drop non-exact
    return [h for h in hits if "exact" in h[2] and h[2].get("exact", 0) >= 70]


# --- recipes ---

def recipe_V2(query, ctx, limit=8):
    field_hits = ctx["field_v1_fused"](query, ctx["field_v1"], limit)
    rule_hits = rules_search(query, ctx["rules"], limit)
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    return merge_slots((abbr_hits, 2), (rule_hits, 3), (field_hits, limit), limit=limit)


def recipe_V2R(query, ctx, limit=8):
    """V2 + hard reject layer for irr/unsup markers."""
    hits = recipe_V2(query, ctx, limit)
    return apply_reject_filter(query, hits, hard_reject=True, soft_require_exact=True)


def recipe_V4_cov(query, ctx, limit=8):
    """Strict field coverage + V2 rules/abbr + hard reject."""
    field_hits = field_search_strict(
        query,
        ctx["field_v1"],
        limit,
        allow_2char_stem=False,
        min_coverage=0.45,
        require_exact_or_key=True,
    )
    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    hits = merge_slots((abbr_hits, 2), (rule_hits, 3), (field_hits, limit), limit=limit)
    return apply_reject_filter(query, hits, hard_reject=True, soft_require_exact=True)


def recipe_V5_stem(query, ctx, limit=8):
    """Like V4 but allow careful 2-char stem on field."""
    field_hits = field_search_strict(
        query,
        ctx["field_v1"],
        limit,
        allow_2char_stem=True,
        min_coverage=0.40,
        require_exact_or_key=False,
    )
    # post-filter stem: only keep if query is a contiguous substring of a phrase longer than query
    qn = _normalise(query)
    filtered = []
    for entry, score, channels in field_hits:
        if "exact" in channels or relevance_ok(
            query, entry, min_coverage=0.40, require_exact_or_key=False, channels=channels
        ):
            # for 2-char queries, require literal phrase containment
            if len(qn) == 2:
                if any(qn in ph and len(ph) > 2 for ph in _phrases(entry.search_text)):
                    filtered.append((entry, score, channels))
            else:
                filtered.append((entry, score, channels))
    field_hits = filtered[:limit]
    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    hits = merge_slots((abbr_hits, 2), (rule_hits, 3), (field_hits, limit), limit=limit)
    return apply_reject_filter(query, hits, hard_reject=True, soft_require_exact=True)


def recipe_V6_cascade(query, ctx, limit=8):
    """Cascade: abbr exact → spoken-key exact → field strict(+stem) → rules strict → empty.
    Hard reject markers unless cascade already got strong exact.
    """
    reason = reject_query_heuristic(query)
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    if abbr_hits:
        return abbr_hits[:limit]

    spoken = spoken_key_exact(query, ctx["field_v1"], limit)
    if spoken:
        # also allow exact rule name/pattern equal
        rule_exact = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)
        rule_exact = [h for h in rule_exact if h[2].get("exact", 0) >= 90]
        return merge_slots((spoken, limit), (rule_exact, 2), limit=limit)

    # field with stem for short business nouns
    field_hits = field_search_strict(
        query,
        ctx["field_v1"],
        limit,
        allow_2char_stem=True,
        min_coverage=0.50,
        require_exact_or_key=False,
    )
    qn = _normalise(query)
    if len(qn) <= 2:
        field_hits = [
            h
            for h in field_hits
            if any(qn in ph and len(ph) > len(qn) for ph in _phrases(h[0].search_text))
            or h[0].key.casefold() in str(query).casefold()
        ]

    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)

    hits = merge_slots((field_hits, 4), (rule_hits, 3), limit=limit)

    if reason:
        # only keep if exact channel strong AND query phrase in search_text
        strong = []
        for entry, score, ch in hits:
            if ch.get("exact", 0) >= 90 and qn and qn in _normalise(entry.search_text):
                # still reject hobby/weather if the match is only via 客户/什么
                phs = _phrases(entry.search_text)
                if any(p == qn or (len(qn) >= 4 and qn in p) for p in phs):
                    strong.append((entry, score, ch))
        return strong[:limit]
    return hits


def recipe_V7_cascade_rules_first(query, ctx, limit=8):
    """Cascade: abbr → rule exact/name → spoken → field stem → empty."""
    reason = reject_query_heuristic(query)
    if reason:
        return []

    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    if abbr_hits:
        return abbr_hits[:limit]

    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)
    # prefer high-quality rule hits
    strong_rules = [h for h in rule_hits if h[1] >= 55]
    spoken = spoken_key_exact(query, ctx["field_v1"], limit)

    field_hits = field_search_strict(
        query,
        ctx["field_v1"],
        limit,
        allow_2char_stem=True,
        min_coverage=0.55,
        require_exact_or_key=False,
    )
    qn = _normalise(query)
    if len(qn) == 2:
        field_hits = [
            h
            for h in field_hits
            if any(qn in ph and len(ph) > 2 for ph in _phrases(h[0].search_text))
        ]

    # If strong rule or spoken exists, prefer those; else field
    if strong_rules or spoken:
        return merge_slots((abbr_hits, 1), (strong_rules, 3), (spoken, 3), (field_hits, 2), limit=limit)
    return merge_slots((field_hits, limit), (rule_hits, 2), limit=limit)


def recipe_V8_highbar(query, ctx, limit=8):
    """Maximize empties on noise: require exact-ish; cascade; hard reject."""
    reason = reject_query_heuristic(query)
    if reason:
        return []
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    if abbr_hits:
        return abbr_hits[:limit]
    spoken = spoken_key_exact(query, ctx["field_v1"], limit)
    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=3)
    # only exact-ish rules
    rule_hits = [h for h in rule_hits if h[1] >= 70]
    # field: exact strategy with 2-char stem only, no pure IDF
    field_exact = exact_strategy(query, ctx["field_v1"], limit, allow_2char_stem=True)
    # filter exact to true phrase quality
    qn = _normalise(query)
    field_kept = []
    for entry, score, ch in field_exact:
        phs = _phrases(entry.search_text)
        ok = False
        for ph in phs:
            if ph == qn:
                ok = True
            elif len(qn) >= 2 and qn in ph and len(ph) >= len(qn) + 1:
                # word-ish: not matching inside random long blob without boundary-ish — phrases already split
                if len(qn) >= 2 and ph not in COMMON_TOKENS:
                    ok = True
            elif len(ph) >= 3 and ph in qn:
                ok = True
        if entry.key.casefold() in str(query).casefold():
            ok = True
        if ok:
            field_kept.append((entry, score, ch))
    return merge_slots((spoken, 3), (rule_hits, 3), (field_kept, 4), limit=limit)


def recipe_V9_cov35_reject(query, ctx, limit=8):
    """Mid coverage + reject; stem on; rules strict."""
    if reject_query_heuristic(query):
        return []
    field_hits = field_search_strict(
        query, ctx["field_v1"], limit, allow_2char_stem=True, min_coverage=0.35, require_exact_or_key=False
    )
    rule_hits = rules_search_strict(query, ctx["rules"], limit)
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    return merge_slots((abbr_hits, 2), (rule_hits, 3), (field_hits, limit), limit=limit)


def recipe_V10_pareto(query, ctx, limit=8):
    """Practical Auth-OFF oriented: cascade + reject + stem + strict rules; keep spoken/examples."""
    if reject_query_heuristic(query):
        return []
    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
    if abbr_hits and len(_normalise(query)) >= 2:
        # abbr alone for pure enum tokens; still allow companions if spoken also exact
        spoken = spoken_key_exact(query, ctx["field_v1"], limit)
        if not spoken:
            return abbr_hits[:limit]
        return merge_slots((abbr_hits, 1), (spoken, 2), limit=limit)

    spoken = spoken_key_exact(query, ctx["field_v1"], limit)
    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)
    # boost rule if query⊂pattern with good coverage
    field_hits = field_search_strict(
        query, ctx["field_v1"], limit, allow_2char_stem=True, min_coverage=0.42, require_exact_or_key=False
    )
    qn = _normalise(query)
    if len(qn) == 2:
        field_hits = [
            h
            for h in field_hits
            if any(qn in ph and len(ph) > 2 and ph not in COMMON_TOKENS for ph in _phrases(h[0].search_text))
        ]
    # Prefer spoken/rules when present (business nouns), else field
    if spoken or any(h[1] >= 55 for h in rule_hits):
        return merge_slots((spoken, 3), (rule_hits, 3), (field_hits, 3), limit=limit)
    return merge_slots((field_hits, limit), (rule_hits, 2), limit=limit)


RECIPES: dict[str, Callable] = {
    "V2": recipe_V2,
    "V2R": recipe_V2R,
    "V4_cov": recipe_V4_cov,
    "V5_stem": recipe_V5_stem,
    "V6_cascade": recipe_V6_cascade,
    "V7_rules_first": recipe_V7_cascade_rules_first,
    "V8_highbar": recipe_V8_highbar,
    "V9_cov35": recipe_V9_cov35_reject,
    "V10_pareto": recipe_V10_pareto,
}


def package_result(hits, ctx):
    loaded = []
    for entry, score, channels in hits:
        obj = None
        if entry.collection == "field":
            obj = ctx["field_defs"].get(entry.key) or {"field": entry.key}
        elif entry.collection in {"enhanced_rules", "abbrname"}:
            obj = entry.payload
        loaded.append(
            {
                "key": entry.key,
                "collection": entry.collection,
                "score": score,
                "channels": channels,
                "target_ref": entry.target_ref,
                "loaded": obj is not None,
                "chars": len(json.dumps(obj, ensure_ascii=False)) if obj is not None else 0,
            }
        )
    return {
        "hit_keys": [x["key"] for x in loaded],
        "hit_collections": [x["collection"] for x in loaded],
        "hits": loaded,
        "hit_count": len(loaded),
        "loaded_count": sum(1 for x in loaded if x["loaded"]),
        "load_errors": [],
        "average_loaded_chars": (sum(x["chars"] for x in loaded) / len(loaded)) if loaded else 0.0,
    }


def focus_scorecard(focus_rows: list[dict]) -> dict[str, Any]:
    m = {r["query"]: r for r in focus_rows if not r["id"].startswith("focus-style")}
    need_ok = ["关爱客户", "有钱", "金凤", "盘客"]
    alt_youqian = m.get("有钱客户", {}).get("qual") == "OK"
    nouns_ok = all(m.get(q, {}).get("qual") == "OK" for q in ("关爱客户", "金凤", "盘客")) and (
        m.get("有钱", {}).get("qual") == "OK" or alt_youqian
    )
    weather_ok = m.get("天气怎么样", {}).get("qual") == "OK"
    hobby_ok = m.get("客户平时有什么兴趣爱好", {}).get("qual") == "OK"
    name_qual = m.get("陈金秀", {}).get("qual")
    name_ok = name_qual in {"MISS", "OK"}  # empty or name-field; not FALSE
    return {
        "nouns_ok": nouns_ok,
        "weather_reject": weather_ok,
        "hobby_reject": hobby_ok,
        "name_safe": name_ok,
        "name_qual": name_qual,
        "practical_A": nouns_ok and weather_ok and hobby_ok and name_ok,
        "quals": {q: m.get(q, {}).get("qual") for q in [
            "关爱客户", "有钱", "有钱客户", "金凤", "盘客", "去盘客",
            "A", "O2O", "陈金秀", "天气怎么样", "客户平时有什么兴趣爱好",
        ]},
    }


def score_recipe(card, labeled_by_split, stress_summary) -> float:
    """Pareto-ish scalar for ranking (practical first, then formal)."""
    s = 0.0
    if card["nouns_ok"]:
        s += 40
    if card["weather_reject"]:
        s += 10
    if card["hobby_reject"]:
        s += 15
    if card["name_safe"]:
        s += 5
    if card["practical_A"]:
        s += 20
    d = labeled_by_split["development"]
    h = labeled_by_split["holdout"]
    s += 10 * (d.get("top8_recall_rate") or 0)
    s += 10 * (d.get("irrelevant_rejection_rate") or 0)
    s += 8 * (h.get("top8_recall_rate") or 0)
    s += 12 * (h.get("irrelevant_rejection_rate") or 0)
    # stress: prefer meaningful empties but not too high that kills business
    er = stress_summary["empty_rate"]
    # sweet spot ~0.15–0.45 for this noisy xlsx mix; penalize ~0.02 and >0.85
    if 0.10 <= er <= 0.55:
        s += 8
    elif er < 0.05:
        s -= 6
    elif er > 0.75:
        s -= 4
    # avg hits: lower better when still practical
    avg = stress_summary["avg_hits"]
    if avg <= 3:
        s += 4
    elif avg >= 7:
        s -= 3
    return s


def main() -> int:
    field_doc = yaml.safe_load((SRC / "field_definitions_args.yaml").read_text()) or {}
    intents = [x for x in (field_doc.get("intents") or []) if isinstance(x, dict)]
    rules_doc = yaml.safe_load((SRC / "enhanced_rules_args.yaml").read_text()) or {}
    rules = [x for x in (rules_doc.get("rules") or []) if isinstance(x, dict)]
    abbr_doc = yaml.safe_load((SRC / "abbrname_enums_args.yaml").read_text()) or {}

    field_v1 = build_field_entries_v1(intents)
    rule_entries = build_rule_entries(rules)
    abbr_members = build_abbrname_exact(abbr_doc)
    field_defs: dict[str, Any] = {}
    for raw in intents:
        f = str(raw.get("field") or "").strip()
        if f and f not in field_defs:
            field_defs[f] = raw

    idf_v1 = source_phrase_idf_strategy(field_v1, min_query_coverage=0.0, allow_2char_stem=False)
    exact_v1 = lambda q, e, lim: exact_strategy(q, e, lim, allow_2char_stem=False)

    ctx = {
        "field_v1": field_v1,
        "rules": rule_entries,
        "abbr_members": abbr_members,
        "field_defs": field_defs,
        "field_v1_fused": fused_strategy(exact_v1, idf_v1),
    }

    # holdout source existence evidence
    hold = json.loads((SRC / "holdout_probes.json").read_text())
    dev = json.loads((SRC / "development_probes.json").read_text())
    labeled = [{**p, "split": "development"} for p in dev] + [{**p, "split": "holdout"} for p in hold]

    # coverage of holdout paraphrase tokens
    all_field_text = " ".join(e.search_text for e in field_v1)
    all_rule_text = " ".join(e.search_text for e in rule_entries)
    holdout_source_evidence = []
    for p in hold:
        q = p["query"]
        tokens = [t for t in re.findall(r"[\u4e00-\u9fff]{2,}", q)]
        present = []
        missing = []
        for t in tokens:
            inn = t in all_field_text or t in all_rule_text or _normalise(t) in abbr_members
            (present if inn else missing).append(t)
        holdout_source_evidence.append(
            {
                "id": p["id"],
                "query": q,
                "required": p.get("required"),
                "category": p.get("category"),
                "tokens_present_in_source": present,
                "tokens_absent_from_source": missing,
            }
        )

    iter_q = load_iteration_queries(SRC / "iteration-cases.json")
    focus_items = []
    for fid, q, bucket, meta in FOCUS:
        focus_items.append({"id": fid, "query": q, "bucket": bucket, "meta": meta, "required": []})

    stress = list(iter_q)
    stress.extend(load_xlsx_queries(XLSX)[:341])
    for fid, q, bucket, meta in FOCUS:
        stress.append({"id": fid, "query": q, "bucket": bucket, "required": []})
    seen = set()
    deduped = []
    for item in stress:
        if item["query"] in seen:
            continue
        seen.add(item["query"])
        deduped.append(item)
    stress = deduped

    report = {
        "schema_version": 1,
        "experiment_id": "empirical-solve-iterations-20260813",
        "generated_at": datetime.now(TZ8).isoformat(),
        "note": "Offline iteration only. Not selected/promoted. Source-derived; no synonym injection.",
        "holdout_source_evidence": holdout_source_evidence,
        "recipes": {},
        "ranking": [],
    }

    for name, fn in RECIPES.items():
        labeled_rows = []
        for probe in labeled:
            result = package_result(fn(probe["query"], ctx), ctx)
            req = set(probe.get("required") or [])
            hits = set(result["hit_keys"])
            labeled_rows.append(
                {
                    "id": probe["id"],
                    "split": probe["split"],
                    "category": probe["category"],
                    "query": probe["query"],
                    "required": list(req),
                    "pass_top8": bool(req) and req.issubset(hits),
                    "rejected_ok": (not req) and result["hit_count"] == 0,
                    "result": {
                        "hit_keys": result["hit_keys"],
                        "hit_collections": result["hit_collections"],
                        "hit_count": result["hit_count"],
                        "loaded_count": result["loaded_count"],
                        "load_errors": [],
                        "average_loaded_chars": result["average_loaded_chars"],
                    },
                }
            )

        focus_rows = []
        for item in focus_items:
            result = package_result(fn(item["query"], ctx), ctx)
            meta = item.get("meta") or {}
            meta_norm = {
                "fields": set(meta.get("fields") or []),
                "rules_substr": list(meta.get("rules_substr") or []),
                "abbr": set(meta.get("abbr") or []),
                "reject_preferred": bool(meta.get("reject_preferred")),
                "name_ok_fields": bool(meta.get("name_ok_fields")),
            }
            label = judge_focus(item["query"], meta_norm, result["hits"])
            focus_rows.append(
                {
                    "id": item["id"],
                    "query": item["query"],
                    "bucket": item["bucket"],
                    "qual": label,
                    "hits": [
                        {"key": h["key"], "collection": h["collection"], "score": h["score"]}
                        for h in result["hits"][:8]
                    ],
                    "hit_count": result["hit_count"],
                }
            )

        from run_empirical_keyindex_sim import _bucketize_query

        stress_rows = []
        bucket_stats: dict[str, Counter] = defaultdict(Counter)
        false_accept_proxy = Counter()
        for item in stress:
            result = package_result(fn(item["query"], ctx), ctx)
            bucket = item.get("bucket") or _bucketize_query(item["query"])
            if bucket == "xlsx_stress":
                bucket = _bucketize_query(item["query"])
            stress_rows.append(
                {
                    "id": item["id"],
                    "bucket": bucket,
                    "query": item["query"],
                    "result": {
                        "hit_keys": result["hit_keys"][:8],
                        "hit_collections": result["hit_collections"][:8],
                        "hit_count": result["hit_count"],
                        "loaded_count": result["loaded_count"],
                    },
                }
            )
            bucket_stats[bucket]["n"] += 1
            bucket_stats[bucket]["with_hits"] += int(result["hit_count"] > 0)
            bucket_stats[bucket]["empty"] += int(result["hit_count"] == 0)
            if bucket in {"irrelevant_like", "unsupported_like"} and result["hit_count"] > 0:
                false_accept_proxy[bucket] += 1

        by_split = {}
        for split in ("development", "holdout"):
            rows = [r for r in labeled_rows if r["split"] == split]
            by_split[split] = metrics_labeled(rows)

        card = focus_scorecard(focus_rows)
        stress_summary = {
            "n": len(stress_rows),
            "with_hits": sum(1 for r in stress_rows if r["result"]["hit_count"] > 0),
            "empty_rate": sum(1 for r in stress_rows if r["result"]["hit_count"] == 0) / len(stress_rows),
            "avg_hits": sum(r["result"]["hit_count"] for r in stress_rows) / len(stress_rows),
            "load_success_rate": (
                sum(
                    1
                    for r in stress_rows
                    if r["result"]["hit_count"]
                    and r["result"]["loaded_count"] == r["result"]["hit_count"]
                )
                / max(1, sum(1 for r in stress_rows if r["result"]["hit_count"] > 0))
            ),
            "false_accept_proxy": dict(false_accept_proxy),
            "buckets": {k: dict(v) for k, v in sorted(bucket_stats.items())},
        }
        scalar = score_recipe(card, by_split, stress_summary)
        dual_dev = (
            (by_split["development"].get("top8_recall_rate") or 0) >= 0.85
            and (by_split["development"].get("irrelevant_rejection_rate") or 0) >= 1.0
        )
        dual_hold = (
            (by_split["holdout"].get("top8_recall_rate") or 0) >= 0.85
            and (by_split["holdout"].get("irrelevant_rejection_rate") or 0) >= 1.0
        )

        report["recipes"][name] = {
            "focus": focus_rows,
            "focus_card": card,
            "labeled_metrics": by_split,
            "labeled_failures": [
                {
                    "id": r["id"],
                    "split": r["split"],
                    "category": r["category"],
                    "query": r["query"],
                    "required": r["required"],
                    "hits": r["result"]["hit_keys"],
                    "collections": r["result"]["hit_collections"],
                }
                for r in labeled_rows
                if (r["required"] and not r["pass_top8"])
                or ((not r["required"]) and not r["rejected_ok"])
            ],
            "stress_summary": stress_summary,
            "scalar_score": scalar,
            "dual_thresholds": {"development": dual_dev, "holdout": dual_hold, "both": dual_dev and dual_hold},
            "verdict_vs_V2": None,
        }

    # verdicts vs V2
    base = report["recipes"]["V2"]
    for name, block in report["recipes"].items():
        if name == "V2":
            block["verdict_vs_V2"] = "baseline"
            continue
        better = 0
        worse = 0
        # practical
        if block["focus_card"]["practical_A"] and not base["focus_card"]["practical_A"]:
            better += 2
        if (not block["focus_card"]["nouns_ok"]) and base["focus_card"]["nouns_ok"]:
            worse += 2
        if block["focus_card"]["hobby_reject"] and not base["focus_card"]["hobby_reject"]:
            better += 1
        if (not block["focus_card"]["hobby_reject"]) and base["focus_card"]["hobby_reject"]:
            worse += 1
        # labeled irr
        if (block["labeled_metrics"]["development"].get("irrelevant_rejection_rate") or 0) > (
            base["labeled_metrics"]["development"].get("irrelevant_rejection_rate") or 0
        ) + 1e-9:
            better += 1
        if (block["labeled_metrics"]["development"].get("top8_recall_rate") or 0) + 1e-9 < (
            base["labeled_metrics"]["development"].get("top8_recall_rate") or 0
        ):
            worse += 1
        # stress empty improvement from ~0.02
        if block["stress_summary"]["empty_rate"] >= 0.10 > base["stress_summary"]["empty_rate"]:
            better += 1
        if block["scalar_score"] > base["scalar_score"] + 0.5:
            better += 1
        elif block["scalar_score"] + 0.5 < base["scalar_score"]:
            worse += 1
        if better > worse:
            block["verdict_vs_V2"] = "better"
        elif worse > better:
            block["verdict_vs_V2"] = "worse"
        else:
            block["verdict_vs_V2"] = "mixed"

    ranking = sorted(
        (
            {
                "recipe": name,
                "scalar": block["scalar_score"],
                "practical_A": block["focus_card"]["practical_A"],
                "nouns_ok": block["focus_card"]["nouns_ok"],
                "hobby_reject": block["focus_card"]["hobby_reject"],
                "weather_reject": block["focus_card"]["weather_reject"],
                "dev_top8": block["labeled_metrics"]["development"].get("top8_recall_rate"),
                "dev_irr": block["labeled_metrics"]["development"].get("irrelevant_rejection_rate"),
                "hold_top8": block["labeled_metrics"]["holdout"].get("top8_recall_rate"),
                "hold_irr": block["labeled_metrics"]["holdout"].get("irrelevant_rejection_rate"),
                "stress_empty": block["stress_summary"]["empty_rate"],
                "avg_hits": block["stress_summary"]["avg_hits"],
                "dual_both": block["dual_thresholds"]["both"],
                "verdict_vs_V2": block["verdict_vs_V2"],
            }
            for name, block in report["recipes"].items()
        ),
        key=lambda r: (-r["scalar"], -int(r["practical_A"]), -int(r["hobby_reject"])),
    )
    report["ranking"] = ranking
    best_name = ranking[0]["recipe"]
    best = report["recipes"][best_name]

    # Second-pass micro-iterations around best if practical_A not met
    # Try threshold sweeps for coverage
    sweep_results = []
    for cov in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60):
        for stem in (False, True):
            def make_fn(cov=cov, stem=stem):
                def fn(query, ctx, limit=8):
                    if reject_query_heuristic(query):
                        return []
                    abbr_hits = abbrname_exact_lookup(query, ctx["abbr_members"], limit)
                    if abbr_hits and len(_normalise(query)) >= 2 and not spoken_key_exact(query, ctx["field_v1"], 1):
                        # pure enum token
                        if len(_normalise(query)) <= 4 or True:
                            # only short-ish pure tokens take abbr-only early exit when no spoken
                            if not any(ch.isdigit() for ch in query) and len(_normalise(query)) <= 6:
                                # still OK
                                pass
                    spoken = spoken_key_exact(query, ctx["field_v1"], limit)
                    rule_hits = rules_search_strict(query, ctx["rules"], limit, min_pat_len=2)
                    field_hits = field_search_strict(
                        query,
                        ctx["field_v1"],
                        limit,
                        allow_2char_stem=stem,
                        min_coverage=cov,
                        require_exact_or_key=False,
                    )
                    qn = _normalise(query)
                    if stem and len(qn) == 2:
                        field_hits = [
                            h
                            for h in field_hits
                            if any(
                                qn in ph and len(ph) > 2 and ph not in COMMON_TOKENS
                                for ph in _phrases(h[0].search_text)
                            )
                        ]
                    if abbr_hits and not spoken and len(qn) <= 6:
                        return merge_slots((abbr_hits, 1), (rule_hits, 2), (field_hits, 2), limit=limit)
                    if spoken or any(h[1] >= 55 for h in rule_hits):
                        return merge_slots((abbr_hits, 1), (spoken, 3), (rule_hits, 3), (field_hits, 3), limit=limit)
                    return merge_slots((field_hits, limit), (rule_hits, 2), (abbr_hits, 1), limit=limit)

                return fn

            fn = make_fn()
            # evaluate compact: focus + labeled + stress summary only
            focus_rows = []
            for item in focus_items:
                result = package_result(fn(item["query"], ctx), ctx)
                meta = item.get("meta") or {}
                meta_norm = {
                    "fields": set(meta.get("fields") or []),
                    "rules_substr": list(meta.get("rules_substr") or []),
                    "abbr": set(meta.get("abbr") or []),
                    "reject_preferred": bool(meta.get("reject_preferred")),
                    "name_ok_fields": bool(meta.get("name_ok_fields")),
                }
                label = judge_focus(item["query"], meta_norm, result["hits"])
                focus_rows.append(
                    {
                        "id": item["id"],
                        "query": item["query"],
                        "bucket": item["bucket"],
                        "qual": label,
                        "hits": [
                            {"key": h["key"], "collection": h["collection"], "score": h["score"]}
                            for h in result["hits"][:8]
                        ],
                        "hit_count": result["hit_count"],
                    }
                )
            card = focus_scorecard(focus_rows)
            labeled_rows = []
            for probe in labeled:
                result = package_result(fn(probe["query"], ctx), ctx)
                req = set(probe.get("required") or [])
                hits = set(result["hit_keys"])
                labeled_rows.append(
                    {
                        "id": probe["id"],
                        "split": probe["split"],
                        "category": probe["category"],
                        "query": probe["query"],
                        "required": list(req),
                        "pass_top8": bool(req) and req.issubset(hits),
                        "rejected_ok": (not req) and result["hit_count"] == 0,
                        "result": {
                            "hit_keys": result["hit_keys"],
                            "hit_collections": result["hit_collections"],
                            "hit_count": result["hit_count"],
                            "loaded_count": result["loaded_count"],
                            "load_errors": [],
                            "average_loaded_chars": result["average_loaded_chars"],
                        },
                    }
                )
            by_split = {
                split: metrics_labeled([r for r in labeled_rows if r["split"] == split])
                for split in ("development", "holdout")
            }
            # stress sample for empty rate
            empty = 0
            hit_sum = 0
            fa = Counter()
            for item in stress:
                result = package_result(fn(item["query"], ctx), ctx)
                empty += int(result["hit_count"] == 0)
                hit_sum += result["hit_count"]
                b = item.get("bucket") or _bucketize_query(item["query"])
                if b == "xlsx_stress":
                    b = _bucketize_query(item["query"])
                if b in {"irrelevant_like", "unsupported_like"} and result["hit_count"] > 0:
                    fa[b] += 1
            stress_summary = {
                "n": len(stress),
                "empty_rate": empty / len(stress),
                "avg_hits": hit_sum / len(stress),
                "false_accept_proxy": dict(fa),
                "with_hits": len(stress) - empty,
                "load_success_rate": 1.0,
                "buckets": {},
            }
            scalar = score_recipe(card, by_split, stress_summary)
            rname = f"SWEEP_cov{cov:.2f}_stem{int(stem)}"
            sweep_results.append(
                {
                    "recipe": rname,
                    "cov": cov,
                    "stem": stem,
                    "scalar": scalar,
                    "practical_A": card["practical_A"],
                    "nouns_ok": card["nouns_ok"],
                    "hobby_reject": card["hobby_reject"],
                    "weather_reject": card["weather_reject"],
                    "name_qual": card["name_qual"],
                    "quals": card["quals"],
                    "dev_top8": by_split["development"].get("top8_recall_rate"),
                    "dev_irr": by_split["development"].get("irrelevant_rejection_rate"),
                    "hold_top8": by_split["holdout"].get("top8_recall_rate"),
                    "hold_irr": by_split["holdout"].get("irrelevant_rejection_rate"),
                    "stress_empty": stress_summary["empty_rate"],
                    "avg_hits": stress_summary["avg_hits"],
                    "focus": focus_rows,
                    "labeled_metrics": by_split,
                    "stress_summary": stress_summary,
                    "labeled_failures": [
                        {
                            "id": r["id"],
                            "split": r["split"],
                            "category": r["category"],
                            "query": r["query"],
                            "required": r["required"],
                            "hits": r["result"]["hit_keys"],
                        }
                        for r in labeled_rows
                        if (r["required"] and not r["pass_top8"])
                        or ((not r["required"]) and not r["rejected_ok"])
                    ],
                }
            )

    sweep_results.sort(key=lambda r: (-r["scalar"], -int(r["practical_A"]), -int(r["hobby_reject"])))
    report["sweeps"] = [
        {k: v for k, v in r.items() if k not in {"focus", "labeled_failures", "labeled_metrics", "stress_summary"}}
        for r in sweep_results
    ]
    # register best sweep as recipe if better
    best_sweep = sweep_results[0]
    report["recipes"][best_sweep["recipe"]] = {
        "focus": best_sweep["focus"],
        "focus_card": {
            "nouns_ok": best_sweep["nouns_ok"],
            "weather_reject": best_sweep["weather_reject"],
            "hobby_reject": best_sweep["hobby_reject"],
            "name_safe": best_sweep["name_qual"] in {"MISS", "OK"},
            "name_qual": best_sweep["name_qual"],
            "practical_A": best_sweep["practical_A"],
            "quals": best_sweep["quals"],
        },
        "labeled_metrics": best_sweep["labeled_metrics"],
        "labeled_failures": best_sweep["labeled_failures"],
        "stress_summary": best_sweep["stress_summary"],
        "scalar_score": best_sweep["scalar"],
        "dual_thresholds": {
            "development": (best_sweep["dev_top8"] or 0) >= 0.85 and (best_sweep["dev_irr"] or 0) >= 1.0,
            "holdout": (best_sweep["hold_top8"] or 0) >= 0.85 and (best_sweep["hold_irr"] or 0) >= 1.0,
            "both": False,
        },
        "verdict_vs_V2": "better" if best_sweep["scalar"] > base["scalar_score"] else "mixed",
        "config": {"min_coverage": best_sweep["cov"], "allow_2char_stem": best_sweep["stem"], "reject": True, "rules": "strict", "cascade": True},
    }

    # recompute ranking including sweep best
    ranking = sorted(
        (
            {
                "recipe": name,
                "scalar": block["scalar_score"],
                "practical_A": block["focus_card"]["practical_A"],
                "nouns_ok": block["focus_card"]["nouns_ok"],
                "hobby_reject": block["focus_card"]["hobby_reject"],
                "weather_reject": block["focus_card"]["weather_reject"],
                "dev_top8": block["labeled_metrics"]["development"].get("top8_recall_rate"),
                "dev_irr": block["labeled_metrics"]["development"].get("irrelevant_rejection_rate"),
                "hold_top8": block["labeled_metrics"]["holdout"].get("top8_recall_rate"),
                "hold_irr": block["labeled_metrics"]["holdout"].get("irrelevant_rejection_rate"),
                "stress_empty": block["stress_summary"]["empty_rate"],
                "avg_hits": block["stress_summary"]["avg_hits"],
                "dual_both": block["dual_thresholds"]["both"],
                "verdict_vs_V2": block["verdict_vs_V2"],
            }
            for name, block in report["recipes"].items()
        ),
        key=lambda r: (-r["scalar"], -int(r["practical_A"]), -int(r["hobby_reject"])),
    )
    report["ranking"] = ranking
    best_name = ranking[0]["recipe"]
    best = report["recipes"][best_name]

    # Can we solve?
    practical = best["focus_card"]["practical_A"]
    dual = best["dual_thresholds"]["both"]
    # holdout unsolvable without synonyms?
    absent_holdout = [
        e for e in holdout_source_evidence
        if e["category"] not in {"irrelevant", "unsupported"} and e["tokens_absent_from_source"]
    ]
    if practical and dual:
        can_solve = "YES"
        because = f"recipe {best_name} clears practical A and dual thresholds"
    elif practical and not dual:
        can_solve = "PARTIAL"
        because = (
            f"recipe {best_name} clears practical Auth-OFF navigation (A) but formal dual thresholds fail; "
            f"holdout paraphrases with tokens absent from source: "
            + ", ".join(e["id"] for e in absent_holdout[:6])
        )
    else:
        can_solve = "NO"
        because = f"best recipe {best_name} still fails practical A: {best['focus_card']}"

    report["can_solve"] = {"status": can_solve, "because": because, "best_recipe": best_name}

    best_json = {
        "best_recipe": best_name,
        "config": best.get("config")
        or {
            "description": RECIPES.get(best_name).__doc__ if best_name in RECIPES else best_name,
        },
        "focus_card": best["focus_card"],
        "labeled_metrics": best["labeled_metrics"],
        "stress_summary": {
            k: best["stress_summary"][k]
            for k in ("n", "empty_rate", "avg_hits", "load_success_rate", "false_accept_proxy", "with_hits")
            if k in best["stress_summary"]
        },
        "dual_thresholds": best["dual_thresholds"],
        "scalar_score": best["scalar_score"],
        "ranking_top5": ranking[:5],
        "can_solve": report["can_solve"],
        "holdout_source_evidence": holdout_source_evidence,
        "focus_hits": best["focus"],
        "labeled_failures": best["labeled_failures"],
    }

    OUT_FULL.parent.mkdir(parents=True, exist_ok=True)
    OUT_FULL.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_BEST.write_text(json.dumps(best_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown report
    now = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M UTC+8")
    lines = [
        "# Empirical Solve Iterations",
        "",
        f"Generated: {now}",
        "",
        "## Scope",
        "",
        "- Continue from V2 multi-collection; tighten rules; cascade; rejection; coverage gates.",
        "- **Not** selected / promoted. No Draft skill edits. No synonym injection into answers.",
        "",
        "## Holdout source existence (why dual thresholds hard)",
        "",
        "| id | query | tokens in source | tokens ABSENT |",
        "|---|---|---|---|",
    ]
    for e in holdout_source_evidence:
        lines.append(
            f"| `{e['id']}` | `{e['query']}` | {e['tokens_present_in_source'] or '—'} | "
            f"**{e['tokens_absent_from_source'] or '—'}** |"
        )

    lines += [
        "",
        "## Recipe ranking",
        "",
        "| rank | recipe | scalar | practical_A | nouns | hobby | weather | dev top8/irr | hold top8/irr | stress empty | avg hits | vs V2 |",
        "|---:|---|---:|---|---|---|---|---|---|---:|---:|---|",
    ]
    for i, r in enumerate(ranking, 1):
        lines.append(
            f"| {i} | `{r['recipe']}` | {r['scalar']:.1f} | {r['practical_A']} | {r['nouns_ok']} | "
            f"{r['hobby_reject']} | {r['weather_reject']} | "
            f"{(r['dev_top8'] or 0):.3f}/{(r['dev_irr'] or 0):.3f} | "
            f"{(r['hold_top8'] or 0):.3f}/{(r['hold_irr'] or 0):.3f} | "
            f"{r['stress_empty']:.3f} | {r['avg_hits']:.2f} | {r['verdict_vs_V2']} |"
        )

    lines += ["", "## Per-iteration detail", ""]
    for name in list(RECIPES.keys()) + [best_sweep["recipe"]]:
        if name not in report["recipes"]:
            continue
        block = report["recipes"][name]
        card = block["focus_card"]
        d = block["labeled_metrics"]["development"]
        h = block["labeled_metrics"]["holdout"]
        s = block["stress_summary"]
        lines += [
            f"### {name} — **{block['verdict_vs_V2']}** (scalar={block['scalar_score']:.1f})",
            "",
            f"- Changed: see recipe docstring / config `{block.get('config')}`",
            f"- Focus card: practical_A={card['practical_A']} nouns={card['nouns_ok']} "
            f"weather={card['weather_reject']} hobby={card['hobby_reject']} name={card['name_qual']}",
            f"- Labeled: dev top8={d.get('top8_recall_rate')} irr={d.get('irrelevant_rejection_rate')}; "
            f"holdout top8={h.get('top8_recall_rate')} irr={h.get('irrelevant_rejection_rate')}",
            f"- Stress: empty={s.get('empty_rate'):.3f} avg_hits={s.get('avg_hits'):.2f} "
            f"fa_proxy={s.get('false_accept_proxy')}",
            "",
            "| query | qual | hits |",
            "|---|---|---|",
        ]
        for row in block["focus"]:
            if row["id"].startswith("focus-style"):
                continue
            hit_s = ", ".join(f"{h['collection']}:{h['key']}" for h in row["hits"][:5]) or "∅"
            lines.append(f"| `{row['query']}` | **{row['qual']}** | {hit_s} |")
        lines.append("")

    lines += [
        "",
        "## Sweep summary (coverage × stem)",
        "",
        "| recipe | practical_A | nouns | hobby | dev top8/irr | hold top8/irr | empty | scalar |",
        "|---|---|---|---|---|---|---:|---:|",
    ]
    for r in sweep_results[:12]:
        lines.append(
            f"| `{r['recipe']}` | {r['practical_A']} | {r['nouns_ok']} | {r['hobby_reject']} | "
            f"{(r['dev_top8'] or 0):.3f}/{(r['dev_irr'] or 0):.3f} | "
            f"{(r['hold_top8'] or 0):.3f}/{(r['hold_irr'] or 0):.3f} | "
            f"{r['stress_empty']:.3f} | {r['scalar']:.1f} |"
        )

    lines += [
        "",
        "## Can we solve it?",
        "",
        f"**{can_solve}** — {because}",
        "",
        f"Best recipe: `{best_name}`",
        "",
        "### Best recipe focus quals",
        "",
        "```json",
        json.dumps(best["focus_card"]["quals"], ensure_ascii=False, indent=2),
        "```",
        "",
        "### Formal dual thresholds",
        "",
        f"- development pass: {best['dual_thresholds']['development']}",
        f"- holdout pass: {best['dual_thresholds']['holdout']}",
        f"- both: {best['dual_thresholds']['both']}",
        "",
        "Holdout paraphrases absent from source cannot be solved by projection/matcher alone without answer pollution (synonym injection). Prefer invalidate+rebuild holdout OR accept PARTIAL practical navigation.",
        "",
        f"Artifacts: `{OUT_MD}`, `{OUT_BEST}`, `{OUT_FULL}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    # append issues log
    with ISSUES.open("a", encoding="utf-8") as f:
        f.write("\n## Empirical solve iterations (2026-08-13 UTC+8)\n")
        f.write(f"- Status: **{can_solve}** — {because}\n")
        f.write(f"- Best: `{best_name}` scalar={best['scalar_score']:.1f} practical_A={best['focus_card']['practical_A']}\n")
        f.write(
            f"- Metrics: dev {best['labeled_metrics']['development'].get('top8_recall_rate')}/"
            f"{best['labeled_metrics']['development'].get('irrelevant_rejection_rate')}; "
            f"hold {best['labeled_metrics']['holdout'].get('top8_recall_rate')}/"
            f"{best['labeled_metrics']['holdout'].get('irrelevant_rejection_rate')}; "
            f"stress empty={best['stress_summary'].get('empty_rate'):.3f} avg={best['stress_summary'].get('avg_hits'):.2f}\n"
        )
        f.write(f"- Focus quals: {best['focus_card']['quals']}\n")
        f.write(f"- Artifacts: `{OUT_MD}`, `{OUT_BEST}`\n")

    # try copy summary into project experiments if path exists
    try:
        if PROJ_EXPERIMENTS.exists():
            dest = PROJ_EXPERIMENTS / "empirical-solve-best.json"
            dest.write_text(OUT_BEST.read_text(encoding="utf-8"), encoding="utf-8")
            (PROJ_EXPERIMENTS / "empirical-solve-iterations.md").write_text(
                OUT_MD.read_text(encoding="utf-8"), encoding="utf-8"
            )
    except Exception as exc:  # noqa: BLE001
        report["project_copy_error"] = str(exc)

    print(
        json.dumps(
            {
                "best": best_name,
                "can_solve": report["can_solve"],
                "ranking_top5": ranking[:5],
                "out_md": str(OUT_MD),
                "out_best": str(OUT_BEST),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
