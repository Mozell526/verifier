#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from impl.core.draft_gate_feedback import build_authority_gate_feedback, write_gate_feedback
from impl.core.investigation import validate_investigation_package
from impl.core.investigation_validation import write_investigation_validation_receipt
from impl.core.project_loader import load_project, resolve_role_assets


def _load_tool_inputs(value: str) -> dict:
    raw = value.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        loaded = json.loads(raw)
    else:
        loaded = json.loads(Path(raw).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError("--tool-inputs must be a JSON object keyed by tool_id")
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one Draft investigation package.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--execute-tools", action="store_true")
    parser.add_argument(
        "--tool-inputs",
        default="",
        help="Inline JSON or JSON file: tool_id -> list of kwargs objects.",
    )
    args = parser.parse_args()
    if args.tool_inputs and not args.execute_tools:
        parser.error("--tool-inputs requires --execute-tools")

    spec = load_project(args.project)
    project_root = spec.project_package_path(
        ".",
        field_path="project.package",
        expected_type="directory",
    )
    package = spec.project_package_path(
        f"draft/investigation/{args.role}",
        field_path=f"verifier.assets.investigation.{args.role}",
        expected_type="directory",
    )
    role_root = Path(__file__).resolve().parents[1]
    tool_module_overrides = {
        item["mapping"].production_path: Path(item["path"])
        for item in resolve_role_assets(spec, args.role, use_candidate=True)
        if item["mapping"].kind == "tool" and item["available"]
    }
    tool_inputs = _load_tool_inputs(args.tool_inputs) if args.tool_inputs else None
    try:
        result = validate_investigation_package(
            package,
            project_root=project_root,
            expected_project_id=args.project,
            expected_role=args.role,
            role_contract_root=role_root,
            execute_tools=args.execute_tools,
            tool_module_overrides=tool_module_overrides,
            tool_test_inputs=tool_inputs,
            source_root=spec.source_root_path() if spec.has_business_source else None,
        )
    except Exception as exc:  # noqa: BLE001 - CLI must preserve gate diagnosis
        feedback = build_authority_gate_feedback(
            project_id=args.project, role=args.role, owner_stage="investigate", error=exc
        )
        feedback_path = project_root / "draft" / ".state" / args.role / "investigation-gate-feedback.json"
        write_gate_feedback(feedback_path, feedback)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        print(feedback["diagnosis"], file=sys.stderr)
        print(f"Harness feedback: {feedback_path}", file=sys.stderr)
        return 1
    if args.execute_tools:
        receipt = write_investigation_validation_receipt(
            spec,
            args.role,
            result,
            tool_inputs or {},
        )
        result["validation_receipt"] = str(receipt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
