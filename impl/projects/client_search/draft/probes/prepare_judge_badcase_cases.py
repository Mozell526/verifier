from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from impl.core.pipeline import live_run
from impl.core.portable_artifact import write_portable_export
from impl.core.schema import SingleTurnCase, to_dict


SELECTED_CASE_IDS = (
    "badcase-001",
    "badcase-012",
    "badcase-033",
    "badcase-126",
    "badcase-167",
)


def _annotation(case: dict[str, Any]) -> str:
    return str(
        ((case.get("intent") or {}).get("user_context") or {}).get(
            "annotation"
        )
        or ""
    ).strip()


def _prepare(case: dict[str, Any]) -> dict[str, Any]:
    request = dict(case.get("live_request") or {})
    trace = live_run(
        "client_search",
        SingleTurnCase(id=str(case["id"]), input=request),
    )
    query = str((case.get("intent") or {}).get("query") or "").strip()
    raw_trace = to_dict(trace)
    raw_output = raw_trace.get("extracted_output") or {}
    extracted_output = {
        key: raw_output[key]
        for key in (
            "conditions",
            "structured_output",
            "query_logic",
            "intent_summary",
            "robot_text",
            "query",
        )
        if key in raw_output
    }
    # Keep the business output and request boundary, but omit model prompt
    # transcripts, matched-pattern dumps, and raw transport payloads. Those
    # are not Judge evidence and make a real badcase unnecessarily expensive.
    trace_payload = {
        key: raw_trace.get(key)
        for key in (
            "trace_id",
            "case_id",
            "project_id",
            "input",
            "normalized_request",
            "scenario",
            "status",
            "ready",
            "reference_contract",
            "application_boundary",
        )
        if raw_trace.get(key) is not None
    }
    trace_payload["extracted_output"] = extracted_output
    return {
        "id": f"source-{case['id']}",
        "source_case_id": case["id"],
        "user_intent": query,
        # Loop runner ignores this field. It is retained only as the human
        # after-the-fact review standard and is never included in Judge input.
        "expected_business_outcome": _annotation(case),
        "trace": trace_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay selected client_search badcases into Judge traces."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument(
        "--case-ids",
        default="",
        help="Optional comma-separated badcase IDs; defaults to the frozen exposed set.",
    )
    args = parser.parse_args()

    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    by_id = {
        str(case.get("id") or ""): case
        for case in source
        if isinstance(case, dict)
    }
    selected_ids = tuple(
        item.strip()
        for item in args.case_ids.split(",")
        if item.strip()
    ) or SELECTED_CASE_IDS
    missing = [case_id for case_id in selected_ids if case_id not in by_id]
    if missing:
        raise ValueError(f"selected badcase IDs are missing: {missing}")

    selected = [by_id[case_id] for case_id in selected_ids]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        prepared = list(executor.map(_prepare, selected))
    write_portable_export(Path(args.output), prepared)
    print(json.dumps({
        "case_count": len(prepared),
        "case_ids": [item["source_case_id"] for item in prepared],
        "output": args.output,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
