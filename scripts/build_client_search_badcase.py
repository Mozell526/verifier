#!/usr/bin/env python3
"""从 bace-标注-simplify.xlsx 抽取 SEARCH_ORIGINAL_CONTENT，生成 client_search badcase mock 数据集。

- 按 query 文本去重（保留首次出现顺序）
- 标注列（ROBOT_TEXT / feedback_question_items / feedback_detail / 标注 / 状态列）
  拼接为「标签：内容」片段，写入 intent.user_context.annotation
- 输出 data/client_search/badcase.json（标准 VNext MockCase 7 字段形状）

用法（agno 环境）：
    python scripts/build_client_search_badcase.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
XLSX_PATH = REPO_ROOT / "data" / "bace-标注-simplify.xlsx"
OUTPUT_PATH = REPO_ROOT / "data" / "client_search" / "badcase.json"

SHEET_NAME = "Sheet1"
QUERY_COLUMN = "SEARCH_ORIGINAL_CONTENT"
STATUS_COLUMN_INDEX = 6  # 第 7 列（表头为 None），值如「已解决」

# (列名, 拼接标签)，按此顺序拼接；空值跳过
ANNOTATION_COLUMNS = [
    ("ROBOT_TEXT", "机器人理解"),
    ("feedback_question_items", "反馈项"),
    ("feedback_detail", "用户反馈"),
    ("标注", "标注"),
    ("status", "状态"),
]

CASE_FIELDS = ("id", "project_id", "scenario", "intent", "live_request", "output", "reference")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def build_annotation_note(row: Dict[str, Any]) -> str:
    parts = []
    for key, label in ANNOTATION_COLUMNS:
        text = _clean(row.get(key))
        if text:
            parts.append(f"{label}：{text}")
    return " | ".join(parts)


def read_rows() -> List[Dict[str, Any]]:
    workbook = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    try:
        sheet = workbook[SHEET_NAME]
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    if not rows:
        raise ValueError(f"{XLSX_PATH} 没有数据行")
    header = list(rows[0])
    column_index = {name: i for i, name in enumerate(header) if isinstance(name, str) and name.strip()}
    if QUERY_COLUMN not in column_index:
        raise ValueError(f"缺少列 {QUERY_COLUMN}，实际表头: {header}")

    data_rows: List[Dict[str, Any]] = []
    for raw in rows[1:]:
        row = {name: raw[i] if i < len(raw) else None for name, i in column_index.items()}
        row["status"] = raw[STATUS_COLUMN_INDEX] if len(raw) > STATUS_COLUMN_INDEX else None
        data_rows.append(row)
    return data_rows


def build_cases(data_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for row in data_rows:
        query = _clean(row.get(QUERY_COLUMN))
        if not query or query in deduped:
            continue
        deduped[query] = row

    cases: List[Dict[str, Any]] = []
    for seq, (query, row) in enumerate(deduped.items(), start=1):
        note = build_annotation_note(row)
        cases.append(
            {
                "id": f"badcase-{seq:03d}",
                "project_id": "client_search",
                "scenario": "badcase",
                "intent": {
                    "user_intent": "",
                    "query": query,
                    "user_context": {"annotation": note} if note else {},
                },
                "live_request": {
                    "user_text": query,
                    "user_id": "eval-user",
                    "trace_id": "",
                    "session_id": "eval-session",
                    "source": "askbob",
                    "extra_input_params": {},
                },
                "output": None,
                "reference": None,
            }
        )
    return cases


def self_check(cases: List[Dict[str, Any]]) -> None:
    seen_ids = set()
    for case in cases:
        missing = [key for key in CASE_FIELDS if key not in case]
        if missing:
            raise ValueError(f"case 缺少字段 {missing}: {case.get('id')}")
        user_text = case["live_request"]["user_text"]
        if not user_text:
            raise ValueError(f"case {case['id']} user_text 为空")
        if case["id"] in seen_ids:
            raise ValueError(f"id 重复: {case['id']}")
        seen_ids.add(case["id"])


def main() -> None:
    data_rows = read_rows()
    cases = build_cases(data_rows)
    self_check(cases)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    annotated = sum(1 for case in cases if case["intent"]["user_context"])
    print(
        f"原始行数: {len(data_rows)} | 去重后: {len(cases)} | "
        f"带标注: {annotated} | 输出: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
