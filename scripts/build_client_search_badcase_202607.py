#!/usr/bin/env python3
"""从 万能营销-生产badcase-simplify.xlsx 生成 client_search badcase mock 数据集（202607 批次）。

- 读取 sheet「客户经营智能体」，前两行为表头（主表头 + 子表头），从第 3 行开始取数据
- 以「输入query」为原始用户输入，过滤空值并按 query 文本去重（保留首次出现顺序）
- 标注列拼接为「标签：内容」片段，写入 intent.user_context.annotation
- case id 优先使用表中「事件ID」（I003 等），缺失时从 I030 起按出现顺序续编（原表最大编号 I029）
- 输出 data/client_search/badcase-202607.json（标准 VNext MockCase 7 字段形状）

用法（agno 环境）：
    python scripts/build_client_search_badcase_202607.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
XLSX_PATH = REPO_ROOT / "data" / "万能营销-生产badcase-simplify.xlsx"
OUTPUT_PATH = REPO_ROOT / "data" / "client_search" / "badcase-202607.json"

SHEET_NAME = "客户经营智能体"
HEADER_ROWS = 2  # 第 1 行主表头，第 2 行子表头
QUERY_COLUMN_INDEX = 3  # 输入query
EVENT_ID_COLUMN_INDEX = 0  # 事件ID
FALLBACK_ID_START = 30  # 原表事件ID最大为 I029，缺失时从 I030 续编

# (列索引, 拼接标签)，按此顺序拼接；空值跳过。截图/日志列（5）为嵌入图片公式，不取。
ANNOTATION_COLUMNS = [
    (1, "事件描述"),
    (2, "测试场景"),
    (4, "对话轮次"),
    (6, "当前状态"),
    (7, "提出日期"),
    (8, "问题类型"),
    (9, "是否修改"),
    (10, "优先级"),
    (12, "期望理解"),
    (11, "备注"),
]

CASE_FIELDS = ("id", "project_id", "scenario", "intent", "live_request", "output", "reference")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _cell(row: tuple, index: int) -> str:
    return _clean(row[index]) if index < len(row) else ""


def build_annotation_note(row: tuple) -> str:
    parts = []
    for index, label in ANNOTATION_COLUMNS:
        text = _cell(row, index)
        if text:
            parts.append(f"{label}：{text}")
    return " | ".join(parts)


def read_data_rows() -> List[tuple]:
    workbook = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    try:
        sheet = workbook[SHEET_NAME]
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    if len(rows) <= HEADER_ROWS:
        raise ValueError(f"{XLSX_PATH} 没有数据行")
    header = rows[0]
    if QUERY_COLUMN_INDEX >= len(header) or _clean(header[QUERY_COLUMN_INDEX]) != "输入query":
        raise ValueError(f"列结构不符：第 {QUERY_COLUMN_INDEX} 列应为「输入query」，实际表头: {header}")
    return rows[HEADER_ROWS:]


def build_cases(data_rows: List[tuple]) -> List[Dict[str, Any]]:
    deduped: Dict[str, tuple] = {}
    for row in data_rows:
        query = _cell(row, QUERY_COLUMN_INDEX)
        if not query or query in deduped:
            continue
        deduped[query] = row

    cases: List[Dict[str, Any]] = []
    fallback_seq = FALLBACK_ID_START
    for query, row in deduped.items():
        event_id = _cell(row, EVENT_ID_COLUMN_INDEX)
        if event_id:
            case_id = event_id
        else:
            case_id = f"I{fallback_seq:03d}"
            fallback_seq += 1
        note = build_annotation_note(row)
        cases.append(
            {
                "id": case_id,
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
        if not case["live_request"]["user_text"]:
            raise ValueError(f"case {case['id']} user_text 为空")
        if case["id"] in seen_ids:
            raise ValueError(f"id 重复: {case['id']}")
        seen_ids.add(case["id"])


def main() -> None:
    data_rows = read_data_rows()
    cases = build_cases(data_rows)
    self_check(cases)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    original_ids = sum(1 for c in cases if int(c["id"][1:]) < FALLBACK_ID_START)
    annotated = sum(1 for c in cases if c["intent"]["user_context"])
    print(
        f"原始数据行: {len(data_rows)} | 去重后: {len(cases)} | "
        f"原表事件ID: {original_ids} | 续编ID: {len(cases) - original_ids} | "
        f"带标注: {annotated} | 输出: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
