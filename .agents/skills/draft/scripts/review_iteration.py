#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from impl.core.draft_role_review import write_draft_role_review
from impl.core.project_loader import load_project
from impl.core.schema import DraftLoopState


def _load_review(value: str) -> Mapping[str, Any]:
    stripped = value.lstrip()
    raw = json.loads(value) if stripped.startswith("{") else json.loads(
        Path(value).read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping):
        raise TypeError("--review must resolve to a JSON object")
    allowed = {
        "decision",
        "route",
        "summary",
        "criteria",
        "contract_coverage",
        "exclusions",
        "flip_labels",
        "knowledge_delta",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"role review input contains unknown field: {unknown[0]}")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and persist one Judge/Mock Draft iteration review."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True, choices=("judge", "mock"))
    parser.add_argument("--review", required=True, help="JSON object or JSON file")
    parser.add_argument("--iteration", type=int, default=0)
    args = parser.parse_args()

    spec = load_project(args.project)
    state_path = spec.project_package_path(
        f"draft/.state/{args.role}/loop.json",
        field_path=f"draft.{args.role}.loop_state",
    )
    state = DraftLoopState.from_mapping(
        json.loads(state_path.read_text(encoding="utf-8"))
    )
    iteration = args.iteration or len(state.iterations)
    if iteration < 1 or iteration > len(state.iterations):
        raise ValueError("--iteration must identify an existing Draft Loop iteration")
    loop_iteration = state.iterations[iteration - 1]
    if loop_iteration.decision:
        raise ValueError("Draft Loop iteration has already been reviewed")
    report_path = loop_iteration.run_report.resolve(
        spec.path_resolver,
        field_path=f"draft_loop.iterations[{iteration - 1}].run_report",
        expected_type="file",
    ).physical
    review = _load_review(args.review)
    if "knowledge_delta" not in review:
        raise ValueError("knowledge_delta is required")
    path = write_draft_role_review(
        spec,
        args.role,
        iteration,
        run_report=report_path,
        decision=str(review.get("decision") or ""),
        route=str(review.get("route") or ""),
        summary=str(review.get("summary") or ""),
        criteria=review.get("criteria") or [],
        contract_coverage=review.get("contract_coverage") or [],
        exclusions=review.get("exclusions") or [],
        flip_labels=review.get("flip_labels") or [],
        knowledge_delta=review.get("knowledge_delta"),
    )
    print(
        json.dumps(
            {
                "project_id": args.project,
                "role": args.role,
                "iteration": iteration,
                "role_review": str(path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
