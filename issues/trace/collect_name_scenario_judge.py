"""Collect live (+ optional current draft judge) for the 1A/4A mixed pack.

Does not patch judge.py. Writes frozen traces for the in-memory overlay.
"""
from __future__ import annotations

import argparse
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from impl.core.pipeline import judge as run_judge
from impl.core.pipeline import live_run
from impl.core.schema import SingleTurnCase, to_dict, trace_extracted_output

ROOT = Path(__file__).resolve().parents[2]
PACK = Path(__file__).with_name("name_scenario_mixed_pack.json")
OUT_DIR = Path(__file__).with_name("name_scenario_runs")
SUMMARY = Path(__file__).with_name("name_scenario_collect.json")

JUDGE_DEFAULT = [
    "I224", "I310", "I336", "I539",  # true names, includes the split
    "I650", "I607", "I358", "I168",  # fake names
    "I007", "I611", "I548", "I485",  # 保单 / 居家潜客 / 家办 / 昊轩
    "I210", "I344",                  # catalog vs catalog-as-name
    "HB001", "HB002", "HB003", "HB004", "HB005", "HB006", "HB007", "HB008",
    "HB009", "HB010", "HB011", "HB012", "HB013", "HB014",
    "HB015", "HB016", "HB017", "HB018",
]


def _fields_values(extracted: dict) -> tuple[list[str], list[str]]:
    conds = extracted.get("conditions") if isinstance(extracted, dict) else None
    if not isinstance(conds, list):
        return [], []
    fields, values = [], []
    for item in conds:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        if field:
            fields.append(field)
        value = item.get("value")
        if isinstance(value, list):
            values.extend(str(part) for part in value)
        elif value is not None:
            values.append(str(value))
    return fields, values


def _judge_status(result) -> tuple[str | None, str]:
    payload = to_dict(result) if result is not None else {}
    if not isinstance(payload, dict):
        return None, ""
    summary = payload.get("summary") or {}
    status = (
        summary.get("fulfillment_status")
        or payload.get("overall_status")
        or payload.get("status")
    )
    reasoning = str(payload.get("reasoning_summary") or summary.get("reasoning") or "")
    return (str(status) if status else None), reasoning


def compact_trace(trace) -> dict:
    extracted = trace_extracted_output(trace) or {}
    if not isinstance(extracted, dict):
        extracted = {}
    fields, values = _fields_values(extracted)
    return {
        "trace_id": getattr(trace, "trace_id", None),
        "fields": fields,
        "values": values,
        "robot_text": extracted.get("robot_text"),
        "matched_patterns": extracted.get("matched_patterns"),
        "intent_summary": extracted.get("intent_summary"),
        "conditions": extracted.get("conditions") or [],
        "extracted": extracted,
    }


def load_pack() -> list[dict]:
    return list(json.loads(PACK.read_text(encoding="utf-8"))["cases"])


def process_one(item: dict, mode: str) -> dict:
    rec = {
        "id": item["id"],
        "query": item["query"],
        "role": item["role"],
        "expected_status": item.get("expected_status"),
        "source": item["source"],
        "live_error": None,
        "judge_error": None,
        "live": None,
        "judge_status": None,
        "judge_reasoning": "",
    }
    case_path = OUT_DIR / f"{item['id']}.json"
    if case_path.exists():
        existing = json.loads(case_path.read_text(encoding="utf-8"))
        rec.update({key: existing.get(key) for key in rec if key in existing})
        if existing.get("judge"):
            rec["judge"] = existing["judge"]

    done_status = rec.get("judge_status")
    if mode in {"judge", "all"} and done_status in {"fulfilled", "not_fulfilled"}:
        print(f"[{item['id']}] {item['query']} mode={mode} skip existing {done_status}", flush=True)
        return rec

    print(f"[{item['id']}] {item['query']} mode={mode}", flush=True)
    try:
        if mode in {"live", "all"} or not rec.get("live"):
            trace = live_run(
                "client_search",
                SingleTurnCase(id=item["id"], input={"user_text": item["query"]}),
            )
            rec["live"] = compact_trace(trace)
            rec["live_error"] = None
            if mode in {"judge", "all"}:
                rec["_trace"] = to_dict(trace)
    except Exception as exc:
        rec["live_error"] = f"{type(exc).__name__}: {exc}"
        print("  live_error", rec["live_error"], flush=True)
        traceback.print_exc()

    if mode in {"judge", "all"} and rec.get("live") and not rec.get("live_error"):
        try:
            from impl.core.schema import RunTrace, normalize_run_trace
            if rec.get("_trace"):
                trace = normalize_run_trace(rec["_trace"])
            elif isinstance(rec.get("live"), dict) and rec["live"].get("extracted"):
                live = rec["live"]
                trace = RunTrace(
                    trace_id=str(live.get("trace_id") or item["id"]),
                    project_id="client_search",
                    case_id=item["id"],
                    input={"user_text": item["query"]},
                    normalized_request={"user_text": item["query"]},
                    extracted_output=live.get("extracted") or {},
                    status="ok",
                )
            else:
                trace = live_run(
                    "client_search",
                    SingleTurnCase(id=item["id"], input={"user_text": item["query"]}),
                )
                rec["live"] = compact_trace(trace)
                rec["_trace"] = to_dict(trace)
            result = run_judge("client_search", trace, user_intent="")
            status, reasoning = _judge_status(result)
            rec["judge_status"] = status
            rec["judge_reasoning"] = reasoning[:500]
            rec["judge"] = to_dict(result)
            rec["judge_error"] = None
            print(f"  judge={status}", flush=True)
        except Exception as exc:
            rec["judge_error"] = f"{type(exc).__name__}: {exc}"
            print("  judge_error", rec["judge_error"], flush=True)
            traceback.print_exc()

    rec.pop("_trace", None)
    case_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rec


def summarize(runs: list[dict]) -> dict:
    compact = []
    for rec in runs:
        item = {k: rec.get(k) for k in rec if k != "judge"}
        if isinstance(item.get("live"), dict):
            live = dict(item["live"])
            live.pop("extracted", None)
            item["live"] = live
        compact.append(item)
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "n": len(compact),
        "live_ok": sum(1 for item in compact if item.get("live") and not item.get("live_error")),
        "judge_ok": sum(1 for item in compact if item.get("judge_status") and not item.get("judge_error")),
        "runs": compact,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("live", "judge", "all"), default="all")
    parser.add_argument("--ids", default="", help="comma-separated ids; empty = pack / default judge set")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--all", action="store_true", help="judge the entire mixed pack, not just JUDGE_DEFAULT")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pack = load_pack()
    wanted = {item.strip() for item in args.ids.split(",") if item.strip()}
    if args.mode == "live":
        cases = [item for item in pack if not wanted or item["id"] in wanted]
    else:
        default_ids = {item["id"] for item in pack} if args.all else set(JUDGE_DEFAULT)
        cases = [item for item in pack if item["id"] in (wanted or default_ids)]

    runs = []
    workers = max(1, args.workers)
    if workers == 1:
        for item in cases:
            runs.append(process_one(item, args.mode))
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(process_one, item, args.mode): item["id"] for item in cases}
            by_id = {}
            for future in as_completed(futures):
                rec = future.result()
                by_id[rec["id"]] = rec
        runs = [by_id[item["id"]] for item in cases]

    summary = summarize(runs)
    summary["mode"] = args.mode
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", SUMMARY, "live_ok", summary["live_ok"], "judge_ok", summary["judge_ok"])


if __name__ == "__main__":
    main()
