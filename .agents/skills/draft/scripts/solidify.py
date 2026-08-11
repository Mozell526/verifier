#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from impl.core.draft_gate_feedback import build_authority_gate_feedback, write_gate_feedback
from impl.core.project_loader import load_project
from impl.core.solidify import write_solidify_receipt


def _load_json(value: str) -> Any:
    stripped = value.lstrip()
    if stripped.startswith(("{", "[")):
        return json.loads(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Judge/Mock Solidify mappings and write an audit receipt."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True, choices=("judge", "mock"))
    parser.add_argument("--mappings", required=True, help="JSON list or JSON file")
    parser.add_argument(
        "--runtime-observables", required=True, help="JSON list or JSON file"
    )
    args = parser.parse_args()

    mappings = _load_json(args.mappings)
    observables = _load_json(args.runtime_observables)
    if not isinstance(mappings, list):
        raise TypeError("--mappings must resolve to a JSON list")
    if not isinstance(observables, list):
        raise TypeError("--runtime-observables must resolve to a JSON list")
    spec = load_project(args.project)
    try:
        path = write_solidify_receipt(
            spec, args.role, mappings=mappings, runtime_observables=observables
        )
    except Exception as exc:  # noqa: BLE001 - CLI must preserve gate diagnosis
        subjects = []
        for observable in observables:
            evidence = str(observable.get("evidence") or "").split("#", 1)[0]
            if not evidence:
                continue
            try:
                raw = json.loads((spec.project_package_path(".") / evidence).read_text(encoding="utf-8"))
                subjects.extend(
                    str(item.get("subject_id"))
                    for item in ((raw.get("checks") or {}).get("claim_gate") or {}).get("probes") or []
                    if isinstance(item, dict) and item.get("subject_id")
                )
            except (OSError, json.JSONDecodeError, TypeError):
                continue
        feedback = build_authority_gate_feedback(
            project_id=args.project, role=args.role, owner_stage="solidify",
            error=exc, affected_subjects=subjects,
        )
        feedback_path = spec.project_package_path(".") / "draft" / ".state" / args.role / "solidify-gate-feedback.json"
        write_gate_feedback(feedback_path, feedback)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        print(feedback["diagnosis"], file=sys.stderr)
        print(f"Harness feedback: {feedback_path}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "project_id": args.project,
                "role": args.role,
                "solidify_receipt": str(path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
