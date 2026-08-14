#!/usr/bin/env python3
"""Render per-case Current/Draft comparison table from frozen Draft Loop facts.

基础列（每轮必出）：case / query 输入 / live 输出 / production <role> 结果 /
draft <role> 结果 / harness 分析。场景列按被测场景扩展：--scenario-columns 传
{"列名": "row 内点号路径"}；role=judge 且任一侧存在 authority 调用时自动追加
authority(production) / authority(draft) 列（调用数 + resolution 状态），插在
production/draft 之后、harness 分析之前。harness 分析由 Harness AI 填写，
渲染器对该列一律写 `-`，不得撰写分析。
输出 Markdown 到 stdout，并默认落盘到 run report 同目录 <NNN>-run-comparison-table.md。模板见 reference/loop-comparison-table.md。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from impl.core.project_loader import load_project
from impl.core.schema import DraftLoopState

FACT_COLUMNS = ("case", "query 输入", "live 输出", "production <role> 结果", "draft <role> 结果")
HARNESS_COLUMN = "harness 分析"
BASE_COLUMNS = FACT_COLUMNS + (HARNESS_COLUMN,)


def _dotted(row: Mapping[str, Any], path: str) -> Any:
    value: Any = row
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            index = int(part)
            value = value[index] if index < len(value) else None
        else:
            return None
    return value


def _cell_text(value: Any, limit: int = 96) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _query(case: Mapping[str, Any]) -> str:
    for key in ("user_intent",):
        if str(case.get(key) or "").strip():
            return str(case[key]).strip()
    trace = case.get("trace") or {}
    if isinstance(trace.get("input"), dict):
        for field in ("user_text", "query", "question", "input"):
            value = trace["input"].get(field)
            if value:
                return str(value)
    return str(case.get("id") or "-")


def _live_output(case: Mapping[str, Any]) -> str:
    trace = case.get("trace") or {}
    extracted = trace.get("extracted_output")
    if isinstance(extracted, dict):
        for key in ("intent_summary", "robot_text", "query"):
            if str(extracted.get(key) or "").strip():
                return _cell_text(str(extracted[key]).strip())
        return _cell_text(extracted)
    if extracted:
        return _cell_text(extracted)
    return "-"


def _side_result(row: Mapping[str, Any], side: str) -> str:
    if row.get(f"{side}_error"):
        return f"ERROR {_cell_text(row[f'{side}_error'], 60)}"
    payload = row.get(side)
    if not isinstance(payload, dict):
        return "-"
    overall = payload.get("overall_fulfillment") or {}
    overall_status = overall.get("status") if isinstance(overall, dict) else None
    parts = []
    for item in payload.get("fulfillment_assessments") or []:
        if isinstance(item, dict):
            parts.append(f"{item.get('expectation_id', '?')}:{item.get('status', '?')}")
    cell = str(overall_status or "-")
    if parts:
        cell += " (" + "；".join(parts) + ")"
    return _cell_text(cell, 160)


def _authority_cell(row: Mapping[str, Any], side: str) -> str:
    runtime = row.get(f"{side}_runtime") or {}
    call_ids = runtime.get("authority_tool_call_ids") or []
    audit = runtime.get("authority_audit") or {}
    if not call_ids:
        return "-"
    statuses = []
    failures = 0
    for call_id in call_ids:
        entry = audit.get(call_id) or {}
        if entry.get("tool_failure"):
            failures += 1
            statuses.append("tool_failure")
        else:
            resolution = entry.get("resolution") or {}
            statuses.append(str(resolution.get("status") or "?"))
    cell = f"{len(call_ids)} calls: {','.join(statuses)}"
    if failures:
        cell += f" (tool_failure={failures})"
    return cell


def _render(
    role: str,
    cases: list[Mapping[str, Any]],
    rows: list[Mapping[str, Any]],
    scenario_columns: Mapping[str, str],
) -> str:
    by_key = {str(c.get("id") or c.get("case_key")): c for c in cases}
    has_authority = any(
        (row.get("current_runtime") or {}).get("authority_tool_call_ids")
        or (row.get("draft_runtime") or {}).get("authority_tool_call_ids")
        for row in rows
    )
    columns = list(FACT_COLUMNS)
    if has_authority:
        columns.append("authority(production)")
        columns.append("authority(draft)")
    for label in scenario_columns:
        columns.append(str(label))
    columns.append(HARNESS_COLUMN)

    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for index, row in enumerate(rows):
        key = str(row.get("case_key") if row.get("case_key") is not None else index)
        case = by_key.get(key, {})
        cells = [
            key,
            _cell_text(_query(case)),
            _cell_text(_live_output(case), 72),
            _side_result(row, "current"),
            _side_result(row, "draft"),
        ]
        if has_authority:
            cells.append(_authority_cell(row, "current"))
            cells.append(_authority_cell(row, "draft"))
        for path in scenario_columns.values():
            cells.append(_cell_text(_dotted(row, path)))
        cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        f"> 对比表由 `render_loop_comparison_table.py` 从冻结 iteration-cases 与 run report 确定性渲染；"
        f"基础列 = case / query 输入 / live 输出 / production {role} 结果 / draft {role} 结果 / harness 分析，"
        f"场景列按被测场景扩展。"
    )
    lines.append("> harness 分析由 Harness AI 填写，不是 Role 判定。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True, choices=("judge", "mock", "attribute"))
    parser.add_argument("--iteration", type=int, default=0)
    parser.add_argument("--run-report", default="")
    parser.add_argument("--cases", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--scenario-columns", default="", help='JSON: {"列名": "row 内点号路径"}')
    args = parser.parse_args()

    spec = load_project(args.project)
    if args.run_report:
        report_path = Path(args.run_report)
    else:
        state_path = spec.project_package_path(
            f"draft/.state/{args.role}/loop.json",
            field_path=f"draft.{args.role}.loop_state",
        )
        state = DraftLoopState.from_mapping(json.loads(state_path.read_text(encoding="utf-8")))
        iteration = args.iteration or len(state.iterations)
        if iteration < 1 or iteration > len(state.iterations):
            raise SystemExit(f"--iteration must identify an existing Draft Loop iteration, got {iteration}")
        report_path = state.iterations[iteration - 1].run_report.resolve(
            spec.path_resolver,
            field_path=f"draft_loop.iterations[{iteration - 1}].run_report",
            expected_type="file",
        ).physical

    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = list(report.get("rows") or [])
    if args.cases:
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    else:
        cases_path = report_path.parent.parent / "iteration-cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise SystemExit("iteration-cases.json must be a list of case objects")

    scenario_columns = json.loads(args.scenario_columns) if args.scenario_columns.strip() else {}
    if not isinstance(scenario_columns, dict):
        raise SystemExit("--scenario-columns must be a JSON object")

    table = _render(args.role, cases, rows, scenario_columns)
    output = Path(args.output) if args.output else report_path.with_name(
        report_path.stem + "-comparison-table.md"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(table, encoding="utf-8")
    print(table)
    print(json.dumps({"project_id": args.project, "role": args.role, "table": str(output),
                      "case_count": len(rows)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
