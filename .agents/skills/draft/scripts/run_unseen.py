#!/usr/bin/env python3
"""在未见对照 case 上运行 current/draft，输出原始结果用于泛化退化判断。

不做分数阈值或字段匹配判断。是否退化由 skill 结合 objective、review 和真实实验决定。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.load_mock_source import load_mock_source  # noqa: E402
from scripts.run_iteration import run_frozen_iteration  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run current/draft on unseen cases for generalization check.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    parser.add_argument("--cases", required=True, help="Path to unseen cases (.json or .py fixture) or inline JSON")
    args = parser.parse_args()

    if args.cases.strip().startswith("["):
        cases = json.loads(args.cases)
    else:
        loaded = load_mock_source(args.cases)
        cases = loaded.get("iteration_cases") or loaded.get("unseen_cases") or []

    if not cases:
        print("unseen cases: empty; generalization check failed", file=sys.stderr)
        return 2

    result = run_frozen_iteration(args.project, args.role, cases)
    print(json.dumps({
        "case_count": result.get("case_count"),
        "rows": result.get("rows"),
        "note": "raw current/draft outputs on unseen cases; decide generalization against review",
    }, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
