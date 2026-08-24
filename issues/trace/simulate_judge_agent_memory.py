"""In-memory judge-agent experiment.

Does not modify official product files.

Two mouths live in this file:

1. Programmatic / geometric decide is a negative control. It classifies
   input shapes. That is the rule-shaped contrast, not the agent.
2. The LLM judge agent is the experiment. The run must disable the geometric
   short-circuit on the *loaded* judge instance and prepend the principle into
   the extras that actually enter the model.

The agent answers one question: did the user get what they asked for?

    Q1  For each delivered field, consume that field's existing standard.
    Q2  Taken together, does this delivery account for the whole request?

Request accounted for and no existing standard fails -> fulfilled.
Request not accounted for, or an existing standard fails -> not_fulfilled.
Delivery unreadable -> unclear.

It does not read pack roles, sample ids, leftover text, or particle tables.
It does not first label the query as name / id / product.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from impl.core.project_loader import load_project
from impl.core.schema import RunTrace
from impl.projects.client_search.draft.field_sufficiency import (
    _ID_FIELDS,
    _NAME_FIELD,
    load_field_standards,
    name_standard_passes,
)

ROOT = Path(__file__).resolve().parents[2]
PACK = Path(__file__).with_name("name_scenario_mixed_pack.json")
RUNS = Path(__file__).with_name("name_scenario_runs")
OLD_DUMP = Path(__file__).with_name("simulate_1a_sufficiency_program.json")
OUT = Path(__file__).with_name("simulate_judge_agent_memory.json")

_CJK_NAME = re.compile(r"^[\u4e00-\u9fff]{2,4}$")

PRINCIPLE_FOR_AGENT = """
你只回答一件事：用户要的事办成了没有。
对任何输入只问两件事，不要先把问句分进题型。

第一问（字段标准）：
交出来的值，够不够撑住它自己那一维已经有的标准。
姓名维用已有姓名标准：2–4 个汉字、有姓、不是产品名/黑名单/业务后缀。
不要再要一份“这是人名”的独立证明。
问句短、没有“姓名是”这类指示词，不能另设门槛。
撑得住就是这一维办成了；撑不住就是这一维没办成。

第二问（请求有没有被说清）：
把当前交出来的这一维当作用户要的事之后，用户还要的事里，还有没有另一件没被交代的事。
没有另一件事：开口。第一问过了 → fulfilled；第一问没过 → not_fulfilled。
还有另一件事：不要把其中一维说成整句办成了。

第二问不是在数汉字，也不是在对字符串。
它问的是：用户要的事，是不是已经被这一维说完了。
不要剥词凑成某一维。不要为样本加例外。不要先给问句贴题型标签。
""".strip()

PRINCIPLE_WITH_Q1_EVIDENCE = """
你只回答一件事：用户要的事办成了没有。
对任何输入只问两件事，不要先把问句分进题型。

第一问（字段标准）：
不要凭语感猜这个值像不像人名。
交出来的每个已有标准字段，会附一条只读检查：够不够撑住该维已经有的标准。
你要消费这条检查，不要另立门槛，也不要忽略它。
撑得住就是这一维办成了；撑不住就是这一维没办成。
问句短、没有“姓名是”这类指示词，不能另设门槛。

第二问（请求有没有被说清）：
只读检查不替你做这一问。
把当前交出来的这一维当作用户要的事之后，用户还要的事里，还有没有另一件没被交代的事。
没有另一件事：开口。第一问过了 → fulfilled；第一问没过 → not_fulfilled。
还有另一件事：不要把其中一维说成整句办成了。

不要剥词凑成某一维。不要为样本加例外。不要先给问句贴题型标签。
""".strip()

PRINCIPLE_T3 = """
你只回答一件事：用户要的事，这次办成了没有。
对任何输入只问下面两件事。不要先给问句贴类型标签。

第一问（已有字段标准）：
对这次交出来的每一个字段：如果该字段已经有标准，就消费那条只读检查，不要另立门槛，也不要忽略它。
如果该字段本轮没有已有标准，不要发明标准，也不要因为没有标准就判这一字段失败。
第一问看的是值对不对得起该字段已经有的标准，不看用户怎么措辞。

第二问（整句有没有被说清）：
把这次交出来的全部条件合在一起，看用户要的事有没有被说完。
还有没被交代的事：整句没办成，输出 not_fulfilled。
没有另一件没被交代的事：再看第一问。
任一已有标准撑不住 → not_fulfilled。
全部已有标准都撑住，或本轮没有任何已有标准 → fulfilled。

交付读不到 → unclear。不要用 unclear 逃避已经能开口的情况。
不要剥词凑字段。不要为样本加例外。
不要先给问句分类再换规则。
不要因为交出来不止一个字段就判失败。
不要因为问句短就另设门槛。
""".strip()

T1_TREATMENT = "current_prompt_plus_memory_principle_shortcircuit_disabled"
T2_TREATMENT = "current_prompt_plus_q1_standard_evidence_shortcircuit_disabled"
T3_TREATMENT = "generic_two_question_request_level_q1_evidence_shortcircuit_disabled"
T4_TREATMENT = "generic_two_question_no_request_shrink_q1_evidence_shortcircuit_disabled"

PRINCIPLE_T4 = """
你只回答一件事：用户要的事，这次办成了没有。
对任何输入只问下面两件事。不要先给问句贴类型标签。

第一问（已有字段标准）：
对这次交出来的每一个字段：如果该字段已经有标准，就消费那条只读检查，不要另立门槛，也不要忽略它。
如果该字段本轮没有已有标准，不要发明标准，也不要因为没有标准就判这一字段失败。
第一问看的是值对不对得起该字段已经有的标准，不看用户怎么措辞。

第二问（整句有没有被说清）：
用户要的事以原始问句为准。摘要、改写、意图标签都不能替换问句。
把这次交出来的全部条件合在一起，对着原始问句看：要的事有没有被说完。
问句里还要了、这次交付却没有对应条件的，就是没说清，输出 not_fulfilled。
不要为了迁就已经交出来的条件，把问句没被覆盖的部分收成语气、修饰、或“没有具体值所以不是条件”。
“查一下 / 帮我找”是说法，不是另一件要办的事。
没有另一件没被交代的事：再看第一问。
任一已有标准撑不住 → not_fulfilled。
全部已有标准都撑住，或本轮没有任何已有标准 → fulfilled。

交付读不到 → unclear。不要用 unclear 逃避已经能开口的情况。
不要剥词凑字段。不要为样本加例外。
不要先给问句分类再换规则。
不要因为交出来不止一个字段就判失败。
不要因为问句短就另设门槛。
""".strip()


def name_standard_reason(value: str, standards) -> tuple[bool, str]:
    text = str(value or "").strip()
    if not _CJK_NAME.fullmatch(text):
        return False, "不是2至4个汉字"
    if text in standards.blacklist:
        return False, "落在该维已有业务黑名单"
    if any(text.endswith(suffix) for suffix in standards.suffixes):
        return False, "带有该维已有业务后缀"
    if text in standards.products:
        return False, "与已有产品名撞车"
    for compound in standards.compounds:
        if text.startswith(compound):
            if len(text) >= len(compound) + 1:
                return True, "2至4个汉字、有已识别复姓、不是产品名/黑名单/业务后缀"
            return False, "复姓后没有名"
    if text[0] in standards.surnames:
        return True, "2至4个汉字、有姓、不是产品名/黑名单/业务后缀"
    return False, "没有该维已识别的姓"


def describe_field_standard(field: str, value: str, standards) -> Optional[tuple[bool, str]]:
    if field == _NAME_FIELD:
        return name_standard_reason(value, standards)
    if field in _ID_FIELDS:
        ok = bool(str(value or "").strip())
        return ok, "该字段已有标准只要求值非空" if ok else "值为空"
    return None


def q1_evidence_text(pairs: Optional[list[tuple[str, str]]], standards) -> str:
    lines = ["只读字段标准检查（按字段给，不是题型分流，也不替你做第二问）："]
    if not pairs:
        lines.append("- 当前交出来的条件读不到。若交付读不到，第二问不要靠猜。")
        return "\n".join(lines)
    for field, value in pairs:
        check = describe_field_standard(field, value, standards)
        shown = str(value)
        if check is None:
            lines.append(
                f"- 字段 {field}，值「{shown}」：该字段本轮没有已有标准检查。不要发明标准，也不要因此判这一字段失败。"
            )
            continue
        passed, reason = check
        verdict = "够撑住该字段已有标准" if passed else "不够撑住该字段已有标准"
        lines.append(f"- 字段 {field}，值「{shown}」：{verdict}。依据：{reason}。")
    return "\n".join(lines)

# Needles are probes, not a type table. Policy is 1A/4A.
NEEDLES = [
    ("SYN-yangjie", "杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-wangkunlin", "王坤林", [("searchClientName", "王坤林")], "fulfilled"),
    ("SYN-zhangwei", "张伟", [("searchClientName", "张伟")], "fulfilled"),
    ("SYN-liming", "李明", [("searchClientName", "李明")], "fulfilled"),
    ("SYN-gongzhan", "共展", [("searchClientName", "共展")], "not_fulfilled"),
    ("SYN-douya", "豆芽", [("searchClientName", "豆芽")], "not_fulfilled"),
    ("SYN-haoxuan", "昊轩", [("searchClientName", "昊轩")], None),
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
    ("SYN-lookup-yangjie", "查一下杨杰", [("searchClientName", "杨杰")], None),
]


# Extra generalization probes. Not part of the frozen T4 12-row score.
# They test whether T4 is a word list or a request-level measurement.
EXTRA_NEEDLES = [
    ("SYN-help-look-yangjie", "帮忙看看杨杰", [("searchClientName", "杨杰")], None),
    ("SYN-please-check-wangkunlin", "请帮我查王坤林", [("searchClientName", "王坤林")], None),
    (
        "SYN-lookup-clientno",
        "帮我查一下这个客户号 C000888123456",
        [("clientNo", "C000888123456")],
        None,
    ),
    ("SYN-zhangwei-policy-nameonly", "张伟保单", [("searchClientName", "张伟")], None),
    (
        "SYN-query-product-both",
        "查询李明的重疾险",
        [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
        None,
    ),
]



# Policy for the agent wave. None = observe only. "not_fulfilled_forbidden"
# means the agent must not call the whole request fulfilled because of name.
LLM_POLICY = {
    "SYN-yangjie": "fulfilled",
    "SYN-wangkunlin": "fulfilled",
    "SYN-zhangwei": "fulfilled",
    "SYN-liming": "fulfilled",
    "I224": "fulfilled",
    "I539": "fulfilled",
    "I336": "fulfilled",
    "HB001": "fulfilled",
    "HB002": "fulfilled",
    "HB003": "fulfilled",
    "HB005": "fulfilled",
    "HB006": "fulfilled",
    "SYN-gongzhan": "not_fulfilled",
    "SYN-douya": "not_fulfilled",
    "I650": "not_fulfilled",
    "I607": "not_fulfilled",
    "SYN-honglian": "not_fulfilled_forbidden",
    "SYN-benefit": "not_fulfilled_forbidden",
    "SYN-lookup-yangjie": None,
    "SYN-help-look-yangjie": None,
    "SYN-please-check-wangkunlin": None,
    "SYN-lookup-clientno": None,
    "SYN-zhangwei-policy-nameonly": "not_fulfilled_forbidden",
    "SYN-query-product-both": "fulfilled",
    "SYN-product": "fulfilled",
    "SYN-concat": "not_fulfilled_forbidden",
    "SYN-name-plus-product-no-name": "not_fulfilled_forbidden",
    "SYN-jinfeng-as-name": "not_fulfilled",
    "SYN-jinfeng-as-product": "fulfilled",
    "SYN-client-no": "fulfilled",
    "HB009": "not_fulfilled_forbidden",
    "HB015": "fulfilled",
    "HB016": "fulfilled",
    "I007": "not_fulfilled",
    "I248": "not_fulfilled_forbidden",
    "I485": None,
}


def score_llm_rows(rows: list[dict]) -> dict:
    must_ok = []
    must_fail = []
    observe = []
    for row in rows:
        policy = LLM_POLICY.get(row["id"], None)
        status = row.get("llm_status")
        item = {
            "id": row["id"],
            "query": row.get("query"),
            "policy": policy,
            "llm_status": status,
            "error": row.get("error"),
        }
        if policy in {"fulfilled", "not_fulfilled"}:
            (must_ok if status == policy and not row.get("error") else must_fail).append(item)
        elif policy == "not_fulfilled_forbidden":
            bad = status == "fulfilled" or bool(row.get("error"))
            (must_fail if bad else must_ok).append(item)
        else:
            observe.append(item)
    return {
        "must_ok": must_ok,
        "must_fail": must_fail,
        "observe": observe,
        "must_ok_n": len(must_ok),
        "must_fail_n": len(must_fail),
    }


class MemoryJudgeAgent:

    """Negative control. This classifies query shapes. It is not the agent."""

    def __init__(self, standards):
        self.standards = standards

    def decide(self, query: str, pairs: Optional[list[tuple[str, str]]]) -> dict:
        query = str(query or "").strip()
        if not query:
            return self._inherit("empty_query", query, pairs)
        if pairs is None:
            return self._inherit("pairs_unreadable", query, pairs)

        delivered = [(str(field), str(value)) for field, value in pairs]

        if _CJK_NAME.fullmatch(query):
            return self._judge_dimension(
                query,
                delivered,
                dimension="name",
                field=_NAME_FIELD,
                passed=name_standard_passes(query, self.standards),
            )

        id_hits = [
            (field, value)
            for field, value in delivered
            if field in _ID_FIELDS and value == query
        ]
        if len(delivered) == 1 and id_hits:
            return {
                "status": "fulfilled",
                "reason": "sufficient_id",
                "dimension": "id",
                "field": delivered[0][0],
                "value": delivered[0][1],
            }

        return self._inherit("not_one_complete_dimension", query, delivered)

    def _judge_dimension(self, query, delivered, dimension, field, passed):
        matched = [(f, v) for f, v in delivered if f == field and v == query]
        if not matched:
            return self._inherit(f"{dimension}_not_delivered", query, delivered)
        extras = [(f, v) for f, v in delivered if not (f == field and v == query)]
        if extras:
            return self._inherit("other_delivery_present", query, delivered)
        if passed:
            return {
                "status": "fulfilled",
                "reason": f"sufficient_{dimension}",
                "dimension": dimension,
                "field": field,
                "value": query,
            }
        return {
            "status": "not_fulfilled",
            "reason": f"{dimension}_standard_fail",
            "dimension": dimension,
            "field": field,
            "value": query,
        }

    @staticmethod
    def _inherit(reason, query, pairs):
        return {
            "status": None,
            "reason": reason,
            "dimension": "",
            "field": "",
            "value": query,
            "pair_count": 0 if pairs is None else len(pairs),
        }


def geometric_decide(query: str, pairs: Optional[list[tuple[str, str]]], standards) -> dict:
    """Negative-control shape: live-first, value equals whole request."""
    query = str(query or "").strip()
    if not query or pairs is None or len(pairs) != 1:
        return {"status": None, "reason": "geometric_miss"}
    field, value = pairs[0]
    if value != query:
        return {"status": None, "reason": "geometric_value_not_query", "field": field}
    if field == _NAME_FIELD:
        ok = name_standard_passes(value, standards)
        return {
            "status": "fulfilled" if ok else "not_fulfilled",
            "reason": "geometric_name",
        }
    if field in _ID_FIELDS:
        return {"status": "fulfilled" if value.strip() else "not_fulfilled", "reason": "geometric_id"}
    return {"status": None, "reason": "geometric_field_not_authorized"}


def _pairs(fields, values) -> list[tuple[str, str]]:
    out = []
    for field, value in zip(fields or [], values or []):
        text = str(value).strip()
        name = str(field).strip()
        if name and text:
            out.append((name, text))
    return out


def pairs_from_live(live: dict) -> list[tuple[str, str]]:
    if not isinstance(live, dict):
        return []
    conditions = live.get("conditions")
    if isinstance(conditions, list) and conditions:
        out = []
        for item in conditions:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            value = item.get("value")
            if isinstance(value, (list, tuple)):
                if len(value) != 1:
                    return out
                value = value[0]
            if field and value is not None and not isinstance(value, dict):
                out.append((field, str(value).strip()))
        if out:
            return out
    return _pairs(live.get("fields") or [], live.get("values") or [])


def make_trace(case_id: str, query: str, pairs: list[tuple[str, str]], extracted: Optional[dict] = None) -> RunTrace:
    conditions = [{"field": field, "operator": "MATCH", "value": value} for field, value in pairs]
    output = dict(extracted or {})
    output.setdefault("conditions", conditions)
    output.setdefault("query", query)
    output.setdefault("query_logic", "AND")
    return RunTrace(
        trace_id=f"mem:{case_id}",
        project_id="client_search",
        case_id=case_id,
        input={"user_text": query},
        normalized_request={"user_text": query, "query": query},
        extracted_output=output,
        status="ok",
    )


def apply_with_inherit(spoken: Optional[str], baseline: Optional[str]) -> Optional[str]:
    return spoken if spoken is not None else baseline


def overlay_044(spoken: Optional[str], baseline: Optional[str]) -> Optional[str]:
    if spoken == "fulfilled":
        return "fulfilled"
    return baseline


def load_runs() -> dict[str, dict]:
    out = {}
    if not RUNS.is_dir():
        return out
    for path in RUNS.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        out[str(payload.get("id") or path.stem)] = payload
    return out


def load_mislifts() -> list[dict]:
    if not OLD_DUMP.is_file():
        return []
    old = json.loads(OLD_DUMP.read_text(encoding="utf-8"))
    wanted = {"I248", "I213", "I154", "I597", "I153", "I031", "I079"}
    rows = []
    for item in old.get("set_a", {}).get("field_only_vs_sufficiency") or []:
        if item.get("id") in wanted:
            rows.append(item)
    return rows


def score_rows(rows: list[dict]) -> dict:
    must = [row for row in rows if row.get("must") is not None]
    inherit = [row for row in rows if row.get("must") is None]
    return {
        "n": len(rows),
        "must_n": len(must),
        "must_ok": sum(1 for row in must if row.get("agent") == row.get("must")),
        "must_fail": [row["id"] for row in must if row.get("agent") != row.get("must")],
        "inherit_spoke": [
            {"id": row["id"], "agent": row.get("agent"), "query": row.get("query")}
            for row in inherit
            if row.get("agent") is not None
        ],
        "true_name_overstrict_fixed": [
            row["id"]
            for row in rows
            if row.get("family") == "true_bare_name"
            and row.get("frozen") == "not_fulfilled"
            and row.get("final_agent") == "fulfilled"
        ],
        "fake_name_wrong_f": [
            row["id"]
            for row in rows
            if row.get("family") in {"fake_name", "business_word_as_name", "toponym_as_name"}
            and row.get("final_agent") == "fulfilled"
        ],
        "mixed_wrong_lift": [
            row["id"]
            for row in inherit
            if row.get("final_agent") == "fulfilled"
            and row.get("frozen") != "fulfilled"
        ],
    }


def row_for(case_id, query, pairs, standards, agent, *, family="", frozen=None, must=None, pack_expected=None):
    spoken = agent.decide(query, pairs)
    geo = geometric_decide(query, pairs, standards)
    return {
        "id": case_id,
        "query": query,
        "family": family,
        "pairs": [{"field": f, "value": v} for f, v in pairs],
        "must": must,
        "pack_expected": pack_expected,
        "frozen": frozen,
        "agent": spoken["status"],
        "agent_reason": spoken["reason"],
        "geometric": geo["status"],
        "geometric_reason": geo.get("reason"),
        "same_as_geometric": spoken["status"] == geo["status"],
        "overlay_044": overlay_044(spoken["status"], frozen),
        "final_agent": apply_with_inherit(spoken["status"], frozen),
        "final_overlay": overlay_044(spoken["status"], frozen),
    }


def run_programmatic(spec, standards) -> dict:
    agent = MemoryJudgeAgent(standards)
    runs = load_runs()
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    pack_rows = []
    for item in pack.get("cases") or []:
        rec = runs.get(item["id"]) or {}
        live = rec.get("live") or {}
        pairs = pairs_from_live(live)
        family = str(item.get("role") or "")
        must = None
        if family == "true_bare_name" and pairs == [(_NAME_FIELD, item["query"])]:
            must = "fulfilled" if name_standard_passes(item["query"], standards) else "not_fulfilled"
        elif family in {"fake_name", "business_word_as_name", "toponym_as_name"} and pairs == [(_NAME_FIELD, item["query"])]:
            must = "fulfilled" if name_standard_passes(item["query"], standards) else "not_fulfilled"
        elif family == "legal_id" and len(pairs) == 1 and pairs[0][0] in _ID_FIELDS and pairs[0][1] == item["query"]:
            must = "fulfilled"
        pack_rows.append(
            row_for(
                item["id"],
                item["query"],
                pairs,
                standards,
                agent,
                family=family,
                frozen=rec.get("judge_status"),
                must=must,
                pack_expected=item.get("expected_status"),
            )
        )

    needle_rows = []
    for case_id, query, pairs, must in NEEDLES:
        needle_rows.append(
            row_for(case_id, query, pairs, standards, agent, family="needle", must=must)
        )

    mislift_rows = []
    for item in load_mislifts():
        pairs = _pairs(item.get("fields") or [], item.get("values") or [])
        mislift_rows.append(
            row_for(
                str(item.get("id")),
                str(item.get("query") or ""),
                pairs,
                standards,
                agent,
                family="field_only_mislift",
                frozen=item.get("current"),
                must=None,
            )
        )

    return {
        "needles": {
            "score": score_rows(needle_rows),
            "rows": needle_rows,
        },
        "mixed_pack": {
            "score": score_rows(pack_rows),
            "rows": pack_rows,
            "note": "pack expected_status is not a ship KPI",
        },
        "field_only_mislifts": {
            "score": score_rows(mislift_rows),
            "rows": mislift_rows,
        },
    }


GEOMETRIC_REASONS = {
    "用户要的就是这一维，并且交出来的值已经按该维标准交齐。",
    "用户要的就是这一维，但交出来的值撑不住该维标准。",
}

LLM_TREATMENT = T1_TREATMENT


def _status_from_result(result) -> dict:
    payload = result
    status = None
    reason = ""
    expected_present = False
    evidence_source = ""
    if hasattr(result, "overall_fulfillment"):
        status = (result.overall_fulfillment or {}).get("status")
        reason = str(getattr(result, "reasoning_summary", "") or "")
        expected_present = getattr(result, "expected", None) is not None
        evidence = list(getattr(result, "evidence", None) or [])
    elif isinstance(payload, dict):
        status = (
            ((payload.get("overall_fulfillment") or {}) if isinstance(payload.get("overall_fulfillment"), dict) else {}).get("status")
            or ((payload.get("summary") or {}) if isinstance(payload.get("summary"), dict) else {}).get("fulfillment_status")
        )
        reason = str(payload.get("reasoning_summary") or "")
        expected_present = payload.get("expected") is not None
        evidence = list(payload.get("evidence") or [])
    else:
        evidence = []
    for item in evidence:
        if isinstance(item, dict) and item.get("source"):
            evidence_source = str(item.get("source"))
            break
    reason_text = reason.strip()
    if reason_text in GEOMETRIC_REASONS or evidence_source == "field_sufficiency":
        source = "geometric"
    else:
        source = "llm"
    return {
        "status": str(status) if status else None,
        "reason": reason[:400],
        "source": source,
        "expected_present": expected_present,
        "evidence_source": evidence_source,
    }


def _exec_module_globals(inst) -> dict:
    """The loaded judge is a freshly exec'd module, often not the imported one."""
    for fn in (
        getattr(type(inst), "reconcile_result", None),
        getattr(type(inst), "pre_judge", None),
        getattr(type(inst), "build_context", None),
    ):
        raw = getattr(fn, "__func__", fn)
        globs = getattr(raw, "__globals__", None)
        if isinstance(globs, dict):
            return globs
    return {}


def _active_principle(treatment: str) -> str:
    if treatment == T4_TREATMENT:
        return PRINCIPLE_T4
    if treatment == T3_TREATMENT:
        return PRINCIPLE_T3
    if treatment == T2_TREATMENT:
        return PRINCIPLE_WITH_Q1_EVIDENCE
    return PRINCIPLE_FOR_AGENT


def _treatment_uses_q1(treatment: str) -> bool:
    return treatment in {T2_TREATMENT, T3_TREATMENT, T4_TREATMENT}


def _pairs_from_trace(trace) -> list[tuple[str, str]]:
    from impl.projects.client_search.draft.field_sufficiency import delivered_pairs

    pairs = delivered_pairs(trace)
    return list(pairs or [])


def _wrap_judge_instance(inst, inject_principle: bool, standards=None, treatment: str = T1_TREATMENT):
    inst.pre_judge = lambda trace, user_intent=None: None
    original_build = inst.build_context
    globs = _exec_module_globals(inst)
    globs["result_if_speaks"] = lambda spec, trace: None
    globs["apply_last_word"] = lambda spec, trace, result: result
    principle = _active_principle(treatment)
    inject_q1_evidence = _treatment_uses_q1(treatment)

    def build_with_principle(trace):
        ctx = original_build(trace)
        extras = list(ctx.get("system_prompt_extras") or [])
        evidence = ""
        if inject_q1_evidence and standards is not None:
            evidence = q1_evidence_text(_pairs_from_trace(trace), standards)
        injected = []
        if inject_principle:
            injected.append(principle)
        if evidence:
            injected.append(evidence)
        if injected:
            extras = [*injected, *extras]
        ctx["system_prompt_extras"] = extras
        gov = ctx.get("context_governance")
        if injected and isinstance(gov, dict):
            segments = list(gov.get("segments") or [])
            segments.insert(
                0,
                {
                    "segment_id": "memory-judge-agent-principle",
                    "source": "memory://simulate_judge_agent_memory.py",
                    "content": "\n\n".join(injected),
                },
            )
            gov["segments"] = segments
        ctx["_memory_principle_injected"] = bool(inject_principle)
        ctx["_memory_q1_evidence"] = evidence
        return ctx

    inst.build_context = build_with_principle
    return inst


def _install_memory_patches(inject_principle: bool, treatment: str = T1_TREATMENT) -> dict:
    """Patch the loader path, not the import-time class.

    load_project_role_instance execs a fresh judge module each time. Patching
    the imported ClientSearchJudge class does not touch that instance.
    """
    import impl.core.pipeline as pipeline
    import impl.core.project_loader as project_loader
    from impl.projects.client_search.draft import field_sufficiency as fs

    originals = {
        "fs_result_if_speaks": fs.result_if_speaks,
        "fs_apply_last_word": fs.apply_last_word,
        "loader": project_loader.load_project_role_instance,
        "pipeline_loader": pipeline.load_project_role_instance,
    }
    fs.result_if_speaks = lambda spec, trace: None
    fs.apply_last_word = lambda spec, trace, result: result

    def wrapped_loader(spec, role, adapter):
        inst = originals["loader"](spec, role, adapter)
        if role == "judge" and inst is not None:
            standards = load_field_standards(spec) if _treatment_uses_q1(treatment) else None
            return _wrap_judge_instance(
                inst,
                inject_principle,
                standards=standards,
                treatment=treatment,
            )
        return inst

    project_loader.load_project_role_instance = wrapped_loader
    pipeline.load_project_role_instance = wrapped_loader
    return originals


def _restore_memory_patches(originals: dict) -> None:
    import impl.core.pipeline as pipeline
    import impl.core.project_loader as project_loader
    from impl.projects.client_search.draft import field_sufficiency as fs

    fs.result_if_speaks = originals["fs_result_if_speaks"]
    fs.apply_last_word = originals["fs_apply_last_word"]
    project_loader.load_project_role_instance = originals["loader"]
    pipeline.load_project_role_instance = originals["pipeline_loader"]


def probe_memory_patch(spec) -> dict:
    """Prove the next LLM wave will hit the agent, not the geometric mouth."""
    from impl.core.project_loader import load_adapter
    from impl.projects.client_search.draft.judge import ClientSearchJudge

    originals = _install_memory_patches(inject_principle=True, treatment=T1_TREATMENT)
    try:
        adapter = load_adapter(spec)
        import impl.core.pipeline as pipeline
        inst = pipeline.load_project_role_instance(spec, "judge", adapter)
        yang = make_trace("probe-yangjie", "杨杰", [("searchClientName", "杨杰")])
        wei = make_trace("probe-zhangwei", "张伟", [("searchClientName", "张伟")])
        gong = make_trace("probe-gongzhan", "共展", [("searchClientName", "共展")])
        hong = make_trace("probe-honglian", "红莲保单", [("searchClientName", "红莲")])
        pre = {
            "yangjie": inst.pre_judge(yang),
            "zhangwei": inst.pre_judge(wei),
            "gongzhan": inst.pre_judge(gong),
            "honglian": inst.pre_judge(hong),
        }
        ctx = inst.build_context(yang)
        extras = list(ctx.get("system_prompt_extras") or [])
        dummy = type("Dummy", (), {})()
        dummy.mark = "keep"
        globs = _exec_module_globals(inst)
        last_word = globs.get("apply_last_word")
        last_out = last_word(spec, yang, dummy) if last_word else None
        imported_speaks = __import__(
            "impl.projects.client_search.draft.field_sufficiency",
            fromlist=["result_if_speaks"],
        ).result_if_speaks(spec, yang)
        return {
            "ok": (
                all(value is None for value in pre.values())
                and extras[:1] == [PRINCIPLE_FOR_AGENT]
                and last_out is dummy
                and imported_speaks is None
            ),
            "pre_judge_all_none": all(value is None for value in pre.values()),
            "pre_judge": {key: (None if value is None else type(value).__name__) for key, value in pre.items()},
            "principle_first": extras[:1] == [PRINCIPLE_FOR_AGENT],
            "principle_present": PRINCIPLE_FOR_AGENT in extras,
            "last_word_identity": last_out is dummy,
            "imported_result_if_speaks_none": imported_speaks is None,
            "instance_module": type(inst).__module__,
            "imported_judge_module": ClientSearchJudge.__module__,
            "same_module_as_import": type(inst).__module__ == ClientSearchJudge.__module__,
            "has_apply_last_word": callable(last_word),
            "extras_head": extras[0][:80] if extras else "",
        }
    finally:
        _restore_memory_patches(originals)



def probe_q1_evidence(spec) -> dict:
    """Prove Q1 evidence is visible and last-word is still identity."""
    from impl.core.project_loader import load_adapter

    originals = _install_memory_patches(inject_principle=True, treatment=T2_TREATMENT)
    try:
        adapter = load_adapter(spec)
        import impl.core.pipeline as pipeline
        inst = pipeline.load_project_role_instance(spec, "judge", adapter)
        standards = load_field_standards(spec)
        yang = make_trace("probe-yangjie", "杨杰", [("searchClientName", "杨杰")])
        wei = make_trace("probe-zhangwei", "张伟", [("searchClientName", "张伟")])
        gong = make_trace("probe-gongzhan", "共展", [("searchClientName", "共展")])
        hong = make_trace("probe-honglian", "红莲保单", [("searchClientName", "红莲")])
        pre = {
            "yangjie": inst.pre_judge(yang),
            "zhangwei": inst.pre_judge(wei),
            "gongzhan": inst.pre_judge(gong),
            "honglian": inst.pre_judge(hong),
        }
        ctx_wei = inst.build_context(wei)
        ctx_gong = inst.build_context(gong)
        extras_wei = list(ctx_wei.get("system_prompt_extras") or [])
        extras_gong = list(ctx_gong.get("system_prompt_extras") or [])
        dummy = type("Dummy", (), {})()
        dummy.mark = "keep"
        globs = _exec_module_globals(inst)
        last_out = globs.get("apply_last_word")(spec, wei, dummy)
        wei_text = "\n".join(extras_wei[:2])
        gong_text = "\n".join(extras_gong[:2])
        return {
            "ok": (
                all(value is None for value in pre.values())
                and extras_wei[:1] == [PRINCIPLE_WITH_Q1_EVIDENCE]
                and "只读字段标准检查" in wei_text
                and "够撑住该字段已有标准" in wei_text
                and "不够撑住该字段已有标准" in gong_text
                and last_out is dummy
            ),
            "pre_judge_all_none": all(value is None for value in pre.values()),
            "principle_first": extras_wei[:1] == [PRINCIPLE_WITH_Q1_EVIDENCE],
            "wei_has_pass": "够撑住该字段已有标准" in wei_text,
            "gong_has_fail": "：不够撑住该字段已有标准" in gong_ev,
            "last_word_identity": last_out is dummy,
            "wei_evidence": (ctx_wei.get("_memory_q1_evidence") or "")[:240],
            "gong_evidence": (ctx_gong.get("_memory_q1_evidence") or "")[:240],
            "yang_reason": name_standard_reason("杨杰", standards),
            "wei_reason": name_standard_reason("张伟", standards),
            "gong_reason": name_standard_reason("共展", standards),
        }
    finally:
        _restore_memory_patches(originals)


def probe_t3(spec) -> dict:
    """Prove T3 principle is generic and still hits the loaded judge."""
    from impl.core.project_loader import load_adapter

    originals = _install_memory_patches(inject_principle=True, treatment=T3_TREATMENT)
    try:
        adapter = load_adapter(spec)
        import impl.core.pipeline as pipeline
        inst = pipeline.load_project_role_instance(spec, "judge", adapter)
        yang = make_trace("probe-yangjie", "杨杰", [("searchClientName", "杨杰")])
        gong = make_trace("probe-gongzhan", "共展", [("searchClientName", "共展")])
        both = make_trace(
            "probe-product",
            "李明的重疾险",
            [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
        )
        ident = make_trace("probe-id", "C000888123456", [("clientNo", "C000888123456")])
        pre = {
            "yangjie": inst.pre_judge(yang),
            "gongzhan": inst.pre_judge(gong),
            "product": inst.pre_judge(both),
            "id": inst.pre_judge(ident),
        }
        ctx_gong = inst.build_context(gong)
        ctx_both = inst.build_context(both)
        ctx_id = inst.build_context(ident)
        extras_gong = list(ctx_gong.get("system_prompt_extras") or [])
        extras_both = list(ctx_both.get("system_prompt_extras") or [])
        extras_id = list(ctx_id.get("system_prompt_extras") or [])
        principle = extras_gong[0] if extras_gong else ""
        banned = ["2–4", "2-4", "有姓", "姓名题", "这一维", "inherit"]
        dummy = type("Dummy", (), {})()
        dummy.mark = "keep"
        globs = _exec_module_globals(inst)
        last_out = globs.get("apply_last_word")(spec, yang, dummy)
        both_text = "\n".join(extras_both[:2])
        id_text = "\n".join(extras_id[:2])
        gong_ev = ctx_gong.get("_memory_q1_evidence") or ""
        return {
            "ok": (
                all(value is None for value in pre.values())
                and extras_gong[:1] == [PRINCIPLE_T3]
                and not any(token in principle for token in banned)
                and "：够撑住该字段已有标准" not in gong_ev
                and "：不够撑住该字段已有标准" in gong_ev
                and "searchClientName" in both_text
                and "pCategorys" in both_text
                and "clientNo" in id_text
                and last_out is dummy
            ),
            "pre_judge_all_none": all(value is None for value in pre.values()),
            "principle_first": extras_gong[:1] == [PRINCIPLE_T3],
            "principle_has_banned": [token for token in banned if token in principle],
            "gong_has_fail": "：不够撑住该字段已有标准" in gong_ev,
            "both_has_two_fields": "searchClientName" in both_text and "pCategorys" in both_text,
            "id_has_client_no": "clientNo" in id_text,
            "last_word_identity": last_out is dummy,
            "both_evidence": (ctx_both.get("_memory_q1_evidence") or "")[:300],
            "id_evidence": (ctx_id.get("_memory_q1_evidence") or "")[:240],
        }
    finally:
        _restore_memory_patches(originals)



def probe_t4(spec) -> dict:
    """Prove T4 keeps the generic two questions and forbids request shrinking."""
    from impl.core.project_loader import load_adapter

    originals = _install_memory_patches(inject_principle=True, treatment=T4_TREATMENT)
    try:
        adapter = load_adapter(spec)
        import impl.core.pipeline as pipeline
        inst = pipeline.load_project_role_instance(spec, "judge", adapter)
        yang = make_trace("probe-yangjie", "杨杰", [("searchClientName", "杨杰")])
        gong = make_trace("probe-gongzhan", "共展", [("searchClientName", "共展")])
        both = make_trace(
            "probe-product",
            "李明的重疾险",
            [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
        )
        ident = make_trace("probe-id", "C000888123456", [("clientNo", "C000888123456")])
        hong = make_trace("probe-honglian", "红莲保单", [("searchClientName", "红莲")])
        pre = {
            "yangjie": inst.pre_judge(yang),
            "gongzhan": inst.pre_judge(gong),
            "product": inst.pre_judge(both),
            "id": inst.pre_judge(ident),
            "honglian": inst.pre_judge(hong),
        }
        ctx_gong = inst.build_context(gong)
        ctx_both = inst.build_context(both)
        ctx_id = inst.build_context(ident)
        extras_gong = list(ctx_gong.get("system_prompt_extras") or [])
        extras_both = list(ctx_both.get("system_prompt_extras") or [])
        extras_id = list(ctx_id.get("system_prompt_extras") or [])
        principle = extras_gong[0] if extras_gong else ""
        banned = ["2–4", "2-4", "有姓", "姓名题", "这一维", "inherit", "对象/凭证", "题型"]
        dummy = type("Dummy", (), {})()
        dummy.mark = "keep"
        globs = _exec_module_globals(inst)
        last_out = globs.get("apply_last_word")(spec, yang, dummy)
        both_text = "\n".join(extras_both[:2])
        id_text = "\n".join(extras_id[:2])
        gong_ev = ctx_gong.get("_memory_q1_evidence") or ""
        return {
            "ok": (
                all(value is None for value in pre.values())
                and extras_gong[:1] == [PRINCIPLE_T4]
                and not any(token in principle for token in banned)
                and "原始问句" in principle
                and "摘要" in principle
                and "：够撑住该字段已有标准" not in gong_ev
                and "：不够撑住该字段已有标准" in gong_ev
                and "searchClientName" in both_text
                and "pCategorys" in both_text
                and "clientNo" in id_text
                and last_out is dummy
            ),
            "pre_judge_all_none": all(value is None for value in pre.values()),
            "principle_first": extras_gong[:1] == [PRINCIPLE_T4],
            "principle_has_banned": [token for token in banned if token in principle],
            "pins_original_utterance": "原始问句" in principle and "摘要" in principle,
            "gong_has_fail": "：不够撑住该字段已有标准" in gong_ev,
            "both_has_two_fields": "searchClientName" in both_text and "pCategorys" in both_text,
            "id_has_client_no": "clientNo" in id_text,
            "last_word_identity": last_out is dummy,
        }
    finally:
        _restore_memory_patches(originals)


def run_llm_agent(
    spec,
    cases: list[dict],
    inject_principle: bool,
    workers: int,
    persist=None,
    treatment: str = T1_TREATMENT,
) -> list[dict]:
    """Run the real judge object in memory. Official files are not written."""
    from impl.core.pipeline import judge as run_judge

    originals = _install_memory_patches(
        inject_principle=inject_principle,
        treatment=treatment,
    )
    rows = []
    lock = Lock()

    def write_partial():
        if persist is None:
            return
        persist(list(rows))

    try:
        def one(item):
            print(f"[llm] start {item['id']} {item['query']}", flush=True)
            trace = make_trace(
                item["id"],
                item["query"],
                item["pairs"],
                extracted=item.get("extracted"),
            )
            try:
                result = run_judge("client_search", trace, user_intent="")
                parsed = _status_from_result(result)
                if parsed["source"] == "geometric":
                    raise RuntimeError(
                        "geometric mouth still speaking; memory patch missed the loaded judge"
                    )
                row = {
                    "id": item["id"],
                    "query": item["query"],
                    "llm_status": parsed["status"],
                    "llm_reason": parsed["reason"],
                    "source": parsed["source"],
                    "expected_present": parsed["expected_present"],
                    "evidence_source": parsed["evidence_source"],
                    "error": None,
                }
            except Exception as exc:
                row = {
                    "id": item["id"],
                    "query": item["query"],
                    "llm_status": None,
                    "llm_reason": "",
                    "source": None,
                    "expected_present": False,
                    "evidence_source": "",
                    "error": f"{type(exc).__name__}: {exc}",
                    "trace": traceback.format_exc()[-500:],
                }
            print(
                f"[llm] done {row['id']} status={row['llm_status']} source={row.get('source')} err={row['error']}",
                flush=True,
            )
            with lock:
                rows.append(row)
                write_partial()
            return row

        if workers <= 1:
            for item in cases:
                one(item)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(one, item) for item in cases]
                for future in as_completed(futures):
                    future.result()
            rows.sort(key=lambda item: item["id"])
    finally:
        _restore_memory_patches(originals)
    return rows


def llm_case_list(programmatic: dict) -> list[dict]:
    runs = load_runs()
    cases = []
    seen = set()
    for group in ("needles", "mixed_pack", "field_only_mislifts"):
        for row in programmatic[group]["rows"]:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            rec = runs.get(row["id"]) or {}
            live = rec.get("live") or {}
            extracted = live.get("extracted") if isinstance(live, dict) else None
            cases.append(
                {
                    "id": row["id"],
                    "query": row["query"],
                    "pairs": [(item["field"], item["value"]) for item in row["pairs"]],
                    "extracted": extracted if isinstance(extracted, dict) else None,
                }
            )
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="also run the real judge agent in memory")
    parser.add_argument("--probe", action="store_true", help="verify the memory patch hits the loaded judge")
    parser.add_argument("--q1-evidence", action="store_true", help="legacy alias for --treatment t2")
    parser.add_argument("--treatment", choices=["t1", "t2", "t3", "t4"], default="", help="which in-memory mouth to run")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ids", default="", help="comma-separated ids for the LLM wave")
    parser.add_argument(
        "--extra-out",
        default="",
        help="write an extra generalization wave here; do not overwrite frozen t1-t4 snaps",
    )
    parser.add_argument(
        "--no-snap",
        action="store_true",
        help="do not rewrite simulate_judge_agent_memory.t1/.t2/.t3/.t4.json",
    )
    args = parser.parse_args()

    spec = load_project("client_search")
    standards = load_field_standards(spec)
    programmatic = run_programmatic(spec, standards)

    if args.treatment == "t4":
        treatment = T4_TREATMENT
    elif args.treatment == "t3":
        treatment = T3_TREATMENT
    elif args.treatment == "t2" or args.q1_evidence:
        treatment = T2_TREATMENT
    elif args.treatment == "t1" or args.llm:
        treatment = T1_TREATMENT
    else:
        treatment = T1_TREATMENT
    inflight = {T1_TREATMENT, T2_TREATMENT, T3_TREATMENT, T4_TREATMENT}
    previous_llm = None
    t1_llm = None
    t2_llm = None
    t3_llm = None
    t4_llm = None
    old_payload = {}
    frozen_t2 = Path(__file__).with_name("simulate_judge_agent_memory.t2-12.json")
    if OUT.is_file():
        try:
            old_payload = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old_payload = {}
    if not old_payload and frozen_t2.is_file():
        try:
            old_payload = json.loads(frozen_t2.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old_payload = {}
    if isinstance(old_payload, dict):
        t1_llm = old_payload.get("llm_t1_principle_only")
        t2_llm = old_payload.get("llm_t2_q1_evidence")
        t3_llm = old_payload.get("llm_t3_generic")
        t4_llm = old_payload.get("llm_t4_no_shrink")
        old_llm = old_payload.get("llm")
        if isinstance(old_llm, dict) and old_llm.get("treatment") == T1_TREATMENT:
            t1_llm = old_llm
        if isinstance(old_llm, dict) and old_llm.get("treatment") == T2_TREATMENT:
            t2_llm = old_llm
        if isinstance(old_llm, dict) and old_llm.get("treatment") == T3_TREATMENT:
            t3_llm = old_llm
        if isinstance(old_llm, dict) and old_llm.get("treatment") == T4_TREATMENT:
            t4_llm = old_llm
        if (
            isinstance(old_llm, dict)
            and old_llm.get("treatment") not in inflight
            and old_llm.get("treatment") != treatment
        ):
            previous_llm = old_llm
        stashed = old_payload.get("llm_previous_wrong_object")
        if previous_llm is None and isinstance(stashed, dict):
            if stashed.get("treatment") not in inflight:
                previous_llm = stashed
    if t2_llm is None and frozen_t2.is_file():
        try:
            frozen = json.loads(frozen_t2.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            frozen = {}
        if isinstance(frozen, dict) and isinstance(frozen.get("llm"), dict):
            if frozen["llm"].get("treatment") == T2_TREATMENT:
                t2_llm = frozen["llm"]

    principle = _active_principle(treatment)

    payload = {
        "note": (
            "In-memory judge agent. Official files were not written by this script. "
            "Mixed-pack expected_status is not a ship KPI. Needles are probes. "
            "Programmatic decide is a negative control, not the product mouth."
        ),
        "principle": principle,
        "treatment": treatment,
        "programmatic": programmatic,
        "probe": old_payload.get("probe") if isinstance(old_payload, dict) else None,
        "llm_previous_wrong_object": previous_llm,
        "llm_t1_principle_only": t1_llm,
        "llm_t2_q1_evidence": t2_llm,
        "llm_t3_generic": t3_llm,
        "llm_t4_no_shrink": t4_llm,
        "llm": (
            t4_llm if treatment == T4_TREATMENT
            else t3_llm if treatment == T3_TREATMENT
            else t2_llm if treatment == T2_TREATMENT
            else t1_llm
        ),
    }

    if args.probe:
        payload["probe"] = probe_memory_patch(spec)
        if treatment == T2_TREATMENT:
            payload["probe_q1"] = probe_q1_evidence(spec)
        if treatment == T3_TREATMENT:
            payload["probe_t3"] = probe_t3(spec)
        if treatment == T4_TREATMENT:
            payload["probe_t4"] = probe_t4(spec)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "probe": payload["probe"],
            "probe_q1": payload.get("probe_q1"),
            "probe_t3": payload.get("probe_t3"),
            "probe_t4": payload.get("probe_t4"),
        }, ensure_ascii=False, indent=2))
        if not payload["probe"].get("ok"):
            raise SystemExit("memory patch probe failed; refusing to spend LLM calls")
        if treatment == T2_TREATMENT and not payload["probe_q1"].get("ok"):
            raise SystemExit("q1 evidence probe failed; refusing to spend LLM calls")
        if treatment == T3_TREATMENT and not payload["probe_t3"].get("ok"):
            raise SystemExit("t3 probe failed; refusing to spend LLM calls")
        if treatment == T4_TREATMENT and not payload["probe_t4"].get("ok"):
            raise SystemExit("t4 probe failed; refusing to spend LLM calls")

    extra_out = Path(args.extra_out).expanduser() if args.extra_out else None
    if extra_out is not None:
        extra_rows = []
        agent = MemoryJudgeAgent(standards)
        for case_id, query, pairs, must in EXTRA_NEEDLES:
            extra_rows.append(row_for(case_id, query, pairs, standards, agent, family="extra", must=must))
        programmatic["extra_needles"] = {"rows": extra_rows, "score": score_rows(extra_rows)}

    if args.llm:
        cases = llm_case_list(programmatic)
        if extra_out is not None:
            cases = [
                {
                    "id": case_id,
                    "query": query,
                    "pairs": list(pairs),
                    "extracted": None,
                }
                for case_id, query, pairs, _must in EXTRA_NEEDLES
            ]
        wanted = {item.strip() for item in args.ids.split(",") if item.strip()}
        if wanted:
            cases = [item for item in cases if item["id"] in wanted]
        existing = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}
        existing_rows = list(existing.get("rows") or []) if existing.get("treatment") == treatment else []
        if extra_out is not None:
            existing_rows = []
        existing_by_id = {row.get("id"): row for row in existing_rows if row.get("id")}
        # resume: do not rerun ids already finished for this treatment
        cases = [item for item in cases if item["id"] not in existing_by_id]

        def merge_llm_rows(new_rows):
            merged = dict(existing_by_id)
            for row in new_rows or []:
                rid = row.get("id")
                if rid:
                    merged[rid] = row
            payload["llm"] = {
                "treatment": treatment,
                "n": len(merged),
                "ids": list(merged),
                "rows": list(merged.values()),
                "score": score_llm_rows(list(merged.values())),
            }
            return payload["llm"]["rows"]

        merge_llm_rows([])

        def persist(rows):
            merge_llm_rows(rows)
            _persist_llm(payload)

        rows = run_llm_agent(
            spec,
            cases,
            inject_principle=True,
            workers=args.workers,
            persist=persist,
            treatment=treatment,
        )
        merge_llm_rows(rows)
        payload["llm_t1_principle_only"] = (
            payload["llm"] if treatment == T1_TREATMENT else payload.get("llm_t1_principle_only")
        )
        payload["llm_t2_q1_evidence"] = (
            payload["llm"] if treatment == T2_TREATMENT else payload.get("llm_t2_q1_evidence")
        )
        payload["llm_t3_generic"] = (
            payload["llm"] if treatment == T3_TREATMENT else payload.get("llm_t3_generic")
        )
        payload["llm_t4_no_shrink"] = (
            payload["llm"] if treatment == T4_TREATMENT else payload.get("llm_t4_no_shrink")
        )
        snap = Path(__file__).with_name(
            "simulate_judge_agent_memory.t4.json" if treatment == T4_TREATMENT
            else "simulate_judge_agent_memory.t3.json" if treatment == T3_TREATMENT
            else "simulate_judge_agent_memory.t2.json" if treatment == T2_TREATMENT
            else "simulate_judge_agent_memory.t1.json"
        )
        if extra_out is not None:
            extra_payload = {
                "note": (
                    "Extra in-memory generalization probes. "
                    "This file is not the frozen T4 12-row score."
                ),
                "principle": principle,
                "treatment": treatment,
                "ids": [item["id"] for item in cases],
                "llm": payload.get("llm"),
            }
            extra_out.write_text(json.dumps(extra_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif not args.no_snap:
            snap.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if extra_out is None:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "out": str(OUT),
        "needles": programmatic["needles"]["score"],
        "mixed_pack": {
            k: programmatic["mixed_pack"]["score"][k]
            for k in (
                "n",
                "must_ok",
                "must_n",
                "must_fail",
                "true_name_overstrict_fixed",
                "fake_name_wrong_f",
                "inherit_spoke",
            )
        },
        "mislifts_spoke": programmatic["field_only_mislifts"]["score"]["inherit_spoke"],
        "probe_ok": None if payload["probe"] is None else payload["probe"].get("ok"),
        "llm_n": None if payload["llm"] is None else payload["llm"]["n"],
        "llm_score": None if not payload["llm"] else {
            "must_ok_n": payload["llm"]["score"]["must_ok_n"],
            "must_fail_n": payload["llm"]["score"]["must_fail_n"],
            "must_fail": [item["id"] for item in payload["llm"]["score"]["must_fail"]],
            "observe": [
                {"id": item["id"], "llm_status": item["llm_status"]}
                for item in payload["llm"]["score"]["observe"]
            ],
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _persist_llm(payload: dict) -> None:
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
