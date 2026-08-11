#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import os
import py_compile
import subprocess
import sys
from pathlib import Path

from impl.core.project_loader import (
    load_adapter,
    load_project,
    load_project_role_instance,
    resolve_project_package_root,
)


def _enable_candidate_role(spec: object, role: str) -> None:
    verifier = getattr(spec, "verifier")
    roles = dict(verifier.get("roles") or {})
    role_config = dict(roles.get(role) or {})
    draft = dict(role_config.get("draft") or {})
    draft.update({"enabled": True, "module": f"project://draft/{role}.py"})
    role_config["draft"] = draft
    roles[role] = role_config
    verifier["roles"] = roles


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a project draft role implementation.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    parser.add_argument(
        "--promotion",
        action="store_true",
        help="Run promotion prechecks: unseen generalization run and knowledge update detection.",
    )
    parser.add_argument(
        "--iteration-cases",
        help="Path or expression that loads the iteration cases. Optional for --promotion.",
    )
    parser.add_argument(
        "--unseen-cases",
        help="Path or expression that loads the unseen cases. Required for --promotion.",
    )
    args = parser.parse_args()

    spec = load_project(args.project)
    project_root = resolve_project_package_root(spec, must_exist=True)
    draft_path = project_root / "draft" / f"{args.role}.py"
    if not draft_path.is_file():
        raise FileNotFoundError(f"draft role not found: {draft_path}")
    py_compile.compile(str(draft_path), doraise=True)

    _enable_candidate_role(spec, args.role)
    instance = load_project_role_instance(spec, args.role, load_adapter(spec))
    if instance is None:
        raise TypeError(f"{args.project}/{args.role} did not load a candidate role instance")
    if inspect.isabstract(instance.__class__):
        raise TypeError(f"{instance.__class__.__name__} has unimplemented abstract methods")
    print(f"{args.project}/{args.role}: {instance.__class__.__name__} validated")

    if not args.promotion:
        return 0

    knowledge_path = Path(__file__).resolve().parents[1] / args.role / "knowledge.md"
    if not knowledge_path.is_file():
        print(f"knowledge update: missing {knowledge_path}")
    else:
        print(f"knowledge update: {knowledge_path} mtime={os.stat(knowledge_path).st_mtime}")

    if not args.unseen_cases:
        print("unseen cases: not provided; cannot run generalization check", file=sys.stderr)
        return 2

    cmd = [
        os.environ.get("PYTHON", sys.executable),
        str(Path(__file__).resolve().parent / "run_unseen.py"),
        "--project", args.project,
        "--role", args.role,
        "--cases", args.unseen_cases,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        print(result.stderr.strip() or "unseen run failed", file=sys.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
