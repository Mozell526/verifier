"""Hit the draft judge sufficiency mouth. Not an overlay script.

Needles and frozen rows are probes. They are not type labels and not a KPI.
field_only stays a negative control: 1A used as if it fulfilled the whole request.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from impl.core.project_loader import load_project
from impl.core.schema import (
    BusinessExpectation,
    FulfillmentAssessment,
    JudgeResult,
    RunTrace,
)
from impl.projects.client_search.draft.field_sufficiency import (
    decide,
    decide_from_trace,
    field_standard,
    load_field_standards,
    result_if_speaks,
)
from impl.projects.client_search.draft.judge import ClientSearchJudge

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "simulate_field_sufficiency_host.json"
JUDGE_PATH = ROOT / "impl/projects/client_search/draft/judge.py"
MODULE_PATH = ROOT / "impl/projects/client_search/draft/field_sufficiency.py"
RUNS = HERE / "name_scenario_runs"
OLD_DUMP = HERE / "simulate_1a_sufficiency_program.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trace(trace_id: str, query: str, pairs: list[tuple[str, str]]) -> RunTrace:
    return RunTrace(
        trace_id=trace_id,
        project_id="client_search",
        input={"user_text": query},
        normalized_request={"user_text": query},
        extracted_output={
            "conditions": [
                {"field": field, "operator": "MATCH", "value": value}
                for field, value in pairs
            ]
        },
    )


def _pairs(fields: list[str], values: list[str]) -> list[tuple[str, str]]:
    return list(zip(fields, values))


def field_only_status(query: str, pairs: list[tuple[str, str]], standards) -> str | None:
    hits = []
    for field, value in pairs:
        if value not in query:
            continue
        judged = field_standard(field, value, standards)
        if judged and judged[1]:
            hits.append((field, value))
    return "fulfilled" if hits else None


def judge_view(spec, judge: ClientSearchJudge, trace: RunTrace) -> dict:
    decision = decide_from_trace(spec, trace)
    spoken = result_if_speaks(spec, trace)
    pre = judge.pre_judge(trace)
    leftover = JudgeResult(
        trace_id=trace.trace_id,
        project_id=trace.project_id,
        business_expectations=[
            BusinessExpectation(expectation_id="llm-core", blocking=True)
        ],
        fulfillment_assessments=[
            FulfillmentAssessment(expectation_id="llm-core", status="not_fulfilled")
        ],
        overall_fulfillment={"status": "not_fulfilled"},
    )
    reconciled = judge.reconcile_result(trace, leftover)
    return {
        "query": decision.query,
        "reason": decision.reason,
        "field": decision.field,
        "value": decision.value,
        "dimension": decision.dimension,
        "decide": decision.status,
        "pre_judge": None if pre is None else pre.overall_fulfillment.get("status"),
        "last_word": reconciled.overall_fulfillment.get("status"),
        "replaced_contract": [
            item.expectation_id for item in reconciled.business_expectations
        ],
        "speaks": decision.speaks,
    }


def main() -> None:
    spec = load_project("client_search")
    standards = load_field_standards(spec)
    judge = ClientSearchJudge(spec)
    host_text = JUDGE_PATH.read_text(encoding="utf-8")

    needles = [
        ("SYN-yangjie", "杨杰", [("searchClientName", "杨杰")], "fulfilled"),
        ("SYN-wang", "王坤林", [("searchClientName", "王坤林")], "fulfilled"),
        ("SYN-gongzhan", "共展", [("searchClientName", "共展")], "not_fulfilled"),
        ("SYN-douya", "豆芽", [("searchClientName", "豆芽")], "not_fulfilled"),
        ("SYN-haoxuan", "昊轩", [("searchClientName", "昊轩")], "not_fulfilled"),
        ("SYN-jinfeng-as-name", "金凤", [("searchClientName", "金凤")], "not_fulfilled"),
        ("SYN-honglian", "红莲保单", [("searchClientName", "红莲")], None),
        ("SYN-benefit", "唐诗颖的生存金有没有领取？", [("searchClientName", "唐诗颖")], None),
        (
            "SYN-product",
            "李明的重疾险",
            [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
            None,
        ),
        (
            "SYN-concat",
            "李明重疾险",
            [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
            None,
        ),
        (
            "SYN-jinfeng-as-product",
            "金凤",
            [("polNoInfo.plancodeinfo.abbrname", "金凤")],
            None,
        ),
        ("SYN-name-plus-product-no-name", "李明的重疾险", [("pCategorys", "疾病保险")], None),
        ("SYN-client-no", "C000888123456", [("clientNo", "C000888123456")], "fulfilled"),
    ]

    needle_rows = []
    for case_id, query, pairs, expect in needles:
        view = judge_view(spec, judge, _trace(case_id, query, pairs))
        ablation = field_only_status(query, pairs, standards)
        row = {
            "id": case_id,
            "expect": expect,
            "field_only": ablation,
            **view,
            "ok": view["decide"] == expect and view["pre_judge"] == expect
            and (view["last_word"] == expect if expect is not None else view["last_word"] == "not_fulfilled"),
        }
        needle_rows.append(row)

    frozen_rows = []
    wanted = {
        "I224", "I539", "I650", "I607", "I210", "I485",
        "HB001", "HB009", "HB015",
    }
    if RUNS.is_dir():
        for path in sorted(RUNS.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_id = str(payload.get("id") or "")
            if case_id not in wanted:
                continue
            live = payload.get("live") or {}
            fields = [str(item) for item in (live.get("fields") or [])]
            values = [str(item) for item in (live.get("values") or [])]
            query = str(payload.get("query") or "")
            pairs = _pairs(fields, values)
            view = judge_view(spec, judge, _trace(case_id, query, pairs))
            frozen_rows.append({
                "id": case_id,
                "current_judge": payload.get("judge_status"),
                "pack_expected": payload.get("expected_status"),
                "field_only": field_only_status(query, pairs, standards),
                **view,
            })

    mislift_ids = {"I248", "I213", "I154", "I597", "I153", "I031", "I079"}
    keep_fail = []
    if OLD_DUMP.is_file():
        old = json.loads(OLD_DUMP.read_text(encoding="utf-8"))
        for item in old.get("set_a", {}).get("field_only_vs_sufficiency") or []:
            if item.get("id") not in mislift_ids:
                continue
            query = str(item.get("query") or "")
            pairs = _pairs(item.get("fields") or [], item.get("values") or [])
            view = judge_view(spec, judge, _trace(str(item["id"]), query, pairs))
            keep_fail.append({
                "id": item.get("id"),
                "current": item.get("current"),
                "old_sufficiency_mode": item.get("sufficiency_mode"),
                "field_only": field_only_status(query, pairs, standards),
                **view,
            })

    prompt_gate_gone = (
        "### 裸词规则" not in host_text
        and "独立姓名证据" not in host_text
        and "result_if_speaks" in host_text
        and "apply_last_word" in host_text
    )
    payload = {
        "note": (
            "This dump hits draft field_sufficiency and ClientSearchJudge. "
            "Needles are probes. Mixed-pack scores are not a KPI."
        ),
        "source_sha256": {
            "field_sufficiency.py": _sha(MODULE_PATH),
            "draft/judge.py": _sha(JUDGE_PATH),
        },
        "host": {
            "bare_name_prompt_gate_removed": prompt_gate_gone,
            "pre_judge_wired": "def pre_judge" in host_text,
            "last_word_wired": "apply_last_word" in host_text,
        },
        "needles": {
            "all_ok": all(row["ok"] for row in needle_rows),
            "failed_ids": [row["id"] for row in needle_rows if not row["ok"]],
            "rows": needle_rows,
        },
        "frozen_mixed": frozen_rows,
        "field_only_mislifts_must_inherit": keep_fail,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(OUT),
        "needles_ok": payload["needles"]["all_ok"],
        "failed_ids": payload["needles"]["failed_ids"],
        "prompt_gate_gone": prompt_gate_gone,
        "mislift_inherit": [
            {
                "id": row["id"],
                "decide": row["decide"],
                "field_only": row["field_only"],
            }
            for row in keep_fail
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
