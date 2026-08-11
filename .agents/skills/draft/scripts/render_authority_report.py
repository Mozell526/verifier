#!/usr/bin/env python3
"""Deterministically render a Judge authority investigation report MD from JSON.

Usage:
  <python> render_authority_report.py <path-to-report.json> [<output.md>]

Output defaults to the JSON path with a .md suffix. Validation of the report
against the investigation package happens via validate_investigation.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from impl.core.schema.investigation_judge import (
    load_authority_investigation_report,
    render_authority_report_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_json", type=Path, help="Path to authority-investigation-report.json")
    parser.add_argument("output_md", nargs="?", type=Path, default=None)
    args = parser.parse_args()
    if not args.report_json.is_file():
        parser.error(f"report JSON not found: {args.report_json}")
    report = load_authority_investigation_report(args.report_json)
    rendered = render_authority_report_markdown(report)
    output = args.output_md or args.report_json.with_suffix(".md")
    output.write_text(rendered, encoding="utf-8")
    print(f"rendered {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
