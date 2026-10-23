"""llm_probe_loop 的内置材料（spec/alg/axis_loop.md §4.1）：标准名 → 取值函数，取自 RunTrace 与场景登记。

一个 case 用一个 Case 对象：trace、场景条目、各轴框的描述。取值函数不调模型、不连外部信息源（知识源目录除外：
要列 ES 的文档数与字段骨架，和现方案的查证首条消息一样）。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from impl.core.axis_loop.materials import Material, Registry
from impl.core.live_protocol import business_call_failure
from impl.projects.llm_probe_loop.business_trace.expectation_material import project_requirements

from .requirements import user_turns
from .sources import expand_sources, union_catalog

TEXT = {"type": "string"}
SOURCE = {"type": "object", "properties": {
    "id": TEXT, "side": TEXT, "turn": TEXT, "component": TEXT, "value": {}, "scope": TEXT,
    "trace_refs": {"type": "array", "items": TEXT}}}
MISSING = {"type": "object", "properties": {"turn": TEXT, "component": TEXT, "reason": TEXT}}


@dataclass(frozen=True)
class Case:
    trace: Any
    scenario_id: str
    scenario: Mapping[str, Any]            # 场景条目（capability_map 里的一条）
    notes: Mapping[str, str]               # 轴 id → 场景里这个轴框的描述（原文，含信息源引用）

    def requirements(self) -> dict:
        """需求侧材料：只有用户原话、历史与判准，看不到交付（spec/alg/expectations.md §2.1）。
        判准取场景里需求轴框的描述（场景描述原文当判准读，同现方案兑现轴自推期望时的口径）。"""
        criterion = expand_sources(self.notes.get("expectations") or "")[0]
        return project_requirements(self.trace, {"criterion": criterion} if criterion else {})


def _deliveries(trace: Any) -> list[dict[str, Any]]:
    turns = []
    for n, record in enumerate(getattr(trace, "turn_records", None) or [], 1):
        output = record.get("extracted_output") if isinstance(record, Mapping) else None
        text = (output or {}).get("output_text") if isinstance(output, Mapping) else None
        if isinstance(text, str):
            turns.append({"turn": f"t{n}", "output_text": text})
    if turns:
        return turns
    output = trace.extracted_output if isinstance(trace.extracted_output, Mapping) else {}
    return [{"turn": "t1", "output_text": str(output.get("output_text") or "")}]


def _business_status(case: Case, _: Mapping) -> dict[str, Any]:
    failure = business_call_failure(case.trace)
    return {"ok": not failure, "error": failure or ""}


def _axis_note(case: Case, context: Mapping) -> str:
    return expand_sources(case.notes.get(context.get("axis") or "") or "", material_catalog=True)[0]


def _knowledge(case: Case, _: Mapping) -> dict[str, Any]:
    catalog, outline = union_catalog(case.notes.values())
    keep = ("uri", "title", "description", "notes", "doc_count")
    return {"catalog": [{k: c.get(k) for k in keep if c.get(k)} for c in catalog], "es_outline": outline}


def registry() -> Registry:
    obj = lambda **props: {"type": "object", "properties": props}
    return Registry([
        Material("case.requirements", obj(sources={"type": "array", "items": SOURCE}, missing={"type": "array", "items": MISSING}),
                 "需求侧材料：各轮用户原话、各轮请求里的历史、业务背景、场景判准，每条标了属于哪一轮（turn=t1/t2…，整案的为 case）；"
                 "看不到交付。按轮切由需求轴的分发脚本做", lambda case, _: case.requirements()),
        Material("case.user_turns", {"type": "array", "items": TEXT}, "用户各轮原话，按先后排列",
                 lambda case, _: user_turns(case.trace)),
        Material("case.deliveries", {"type": "array", "items": obj(turn=TEXT, output_text=TEXT)},
                 "被测系统各轮的交付文本", lambda case, _: _deliveries(case.trace)),
        Material("case.final_output", TEXT, "被测系统最后一轮的交付文本（核事实只抽它，同现方案）",
                 lambda case, _: str((case.trace.extracted_output or {}).get("output_text") or "")),
        Material("case.business_status", obj(ok={"type": "boolean"}, error=TEXT), "被测系统这次有没有正常返回",
                 _business_status),
        Material("scenario.boundary", TEXT, "责任范围登记",
                 lambda case, _: str(case.scenario.get("boundary") or "")),
        Material("scenario.knowledge", obj(catalog={"type": "array", "items": obj(uri=TEXT, title=TEXT, description=TEXT, notes=TEXT,
                                                                                    doc_count={"type": "integer"})},
                                          es_outline={"type": "array"}),
                 "场景选用的知识源目录（读法说明、ES 字段骨架）", _knowledge),
        Material("axis.note", TEXT, "场景对当前这个轴写的描述", _axis_note),
    ])
