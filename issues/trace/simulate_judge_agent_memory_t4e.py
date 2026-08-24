"""In-memory T4e mouth. Official files are not written.

T4e keeps the same two questions as T4/T4d. It does not add locutions,
type tables, or a 保单/保单号 lexicon. It only retargets Q2:

    Q2 measures the retrieval keys this request actually gave,
    not every noun that appeared in the sentence.

I007 (name + valueless field name, only the name delivered) is fulfilled.
That is the project lock, not an I007 exception branch.

Writes only to simulate_judge_agent_memory.t4e-extra.json.
Never overwrites the frozen t1/t2/t3/t4 dumps or the live t4 dump.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import simulate_judge_agent_memory as sim

OUT = HERE / "simulate_judge_agent_memory.t4e-extra.json"
LIVE = HERE / "simulate_judge_agent_memory.json"
FROZEN_T4 = HERE / "simulate_judge_agent_memory.t4.json"
OFFICIAL_KPI = HERE / "head_set_b_official_live_kpi.json"
HEAD_SET_B = ROOT / "impl/projects/client_search/draft/cases/head_set_b.json"

T4E_TREATMENT = "generic_two_question_retrieval_keys_q1_q2_shortcircuit_disabled"

PRINCIPLE_T4E = """
你只回答一件事：用户要的事，这次办成了没有。
对任何输入只问下面两件事。两问互相独立，谁也不能替谁回答。
不要先给问句贴类型标签。不要发明第三问。

第一问（已有字段标准）：
对这次交出来的每一个字段：如果该字段已经有标准，必须消费那条只读检查，不要另立门槛，也不要忽略它。
值跟问句写的一样，不是标准。
如果该字段本轮没有已有标准，不要发明标准，也不要因为没有标准就判这一字段失败。
第一问看的是值对不对得起该字段已经有的标准，不看用户怎么提出这次请求。
不要因为问句短、或问句只是一个词，就另设门槛。
第二问看起来已经说完，不能用来跳过第一问。

第二问（整句有没有被说清）：
用户要的事以原始问句为准。摘要、改写、意图标签都不能替换问句。
把这次交出来的全部条件合在一起，对着原始问句看：
这次实际给出的、能够用来查找或筛选的依据，是否都有对应交付。

能够用来查找或筛选的依据：问句里给出的、可以拿去找人或收窄集合的内容。
只是在发出这次请求的部分，不是另一件要办的事。
只点了某个字段的名字、没有给出可用来查找的值，不是另一件必须交出来的条件；也不许为此虚构一个值。
已经给出了可用来查找或筛选的值，却没有对应交付，就是没说清。
第一问过了，不能用来证明第二问过了。

先书面回答第一问，再书面回答第二问。
任一已有标准撑不住 → not_fulfilled。
这次实际给出的查找或筛选依据没有对应交付 → not_fulfilled。
全部已有标准都撑住，或本轮没有任何已有标准，并且这些依据都有对应交付 → fulfilled。

交付读不到 → unclear。不要用 unclear 逃避已经能开口的情况。
不要剥词凑字段。不要为样本加例外。
不要先给问句分类再换规则。
不要因为交出来不止一个字段就判失败。
不要因为问句短就另设门槛。
不要问检索结果集会不会变。
""".strip()

# id, query, pairs, policy
# policy None = observe
# I007 = F is the project lock. Same pattern as I007 is also F.
# 红莲保单 / 张伟保单 stay observe; do not inherit I007.
T4E_NEEDLES = [
    ("SYN-yangjie", "杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-gongzhan", "共展", [("searchClientName", "共展")], "not_fulfilled"),
    ("I007", "张忠波保单号", [("searchClientName", "张忠波")], "fulfilled"),
    ("I248", "红莲保单", [("searchClientName", "红莲")], None),
    ("SYN-help-look-yangjie", "帮忙看看杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-please-find-yangjie", "麻烦找下杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-show-me-wangkunlin", "给我看看王坤林", [("searchClientName", "王坤林")], "fulfilled"),
    ("SYN-help-look-gongzhan", "帮忙看看共展", [("searchClientName", "共展")], "not_fulfilled"),
    ("SYN-zhangwei-policy-nameonly", "张伟保单", [("searchClientName", "张伟")], None),
    ("SYN-zhangwei-policyno-nameonly", "张伟的保单号", [("searchClientName", "张伟")], "fulfilled"),
    (
        "SYN-query-product-both",
        "查询李明的重疾险",
        [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
        "fulfilled",
    ),
    ("HB009-needle", "李明的重疾险", [("pCategorys", "疾病保险")], "not_fulfilled"),
    (
        "SYN-lookup-clientno",
        "帮我查一下这个客户号 C000888123456",
        [("clientNo", "C000888123456")],
        "fulfilled",
    ),
    ("SYN-holdout-please-yangjie", "劳驾查下杨杰", [("searchClientName", "杨杰")], None),
    ("SYN-holdout-please-gongzhan", "劳驾查下共展", [("searchClientName", "共展")], None),
    ("SYN-holdout-zhangwei-policy-info", "张伟保单信息", [("searchClientName", "张伟")], None),
]


def _patch() -> None:
    orig_active = sim._active_principle
    orig_q1 = sim._treatment_uses_q1

    def active(treatment: str) -> str:
        if treatment == T4E_TREATMENT:
            return PRINCIPLE_T4E
        return orig_active(treatment)

    def uses_q1(treatment: str) -> bool:
        if treatment == T4E_TREATMENT:
            return True
        return orig_q1(treatment)

    sim._active_principle = active
    sim._treatment_uses_q1 = uses_q1


def _extracted_for(case_id: str, runs: dict) -> dict | None:
    rec = runs.get(case_id) or {}
    live = rec.get("live") or {}
    extracted = live.get("extracted") if isinstance(live, dict) else None
    return extracted if isinstance(extracted, dict) else None


def _pairs_from_live(rec: dict) -> list[tuple[str, str]]:
    live = rec.get("live") or {}
    conds = live.get("conditions") or []
    pairs = []
    for item in conds:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        value = item.get("value")
        if not field:
            continue
        if isinstance(value, list):
            if not value:
                continue
            value = value[0]
        pairs.append((field, str(value) if value is not None else ""))
    return pairs


def _set_b_policy(cls: str, pairs: list[tuple[str, str]], expected_fields: list[str]) -> str | None:
    delivered = {field for field, _value in pairs}
    missing = [field for field in expected_fields if field not in delivered]
    if cls == "bare_name":
        return "fulfilled" if "searchClientName" in delivered else "not_fulfilled"
    if cls == "legal_id":
        return "fulfilled" if not missing else "not_fulfilled"
    if cls == "name_plus_product":
        # Judge scores the delivery it sees. Missing name is honest NF.
        return "fulfilled" if not missing else "not_fulfilled"
    return None


def _score(rows: list[dict], catalog: list[tuple[str, str, object, str | None]]) -> dict:
    by_id = {row["id"]: row for row in rows}
    must_ok = []
    must_fail = []
    observe = []
    for case_id, query, _pairs, policy in catalog:
        row = by_id.get(case_id) or {
            "id": case_id,
            "query": query,
            "llm_status": None,
            "error": "missing",
        }
        status = row.get("llm_status")
        item = {
            "id": case_id,
            "query": query,
            "policy": policy,
            "llm_status": status,
            "error": row.get("error"),
        }
        if policy is None:
            observe.append(item)
        elif status == policy and not row.get("error"):
            must_ok.append(item)
        else:
            must_fail.append(item)
    return {
        "must_ok": must_ok,
        "must_fail": must_fail,
        "observe": observe,
        "must_ok_n": len(must_ok),
        "must_fail_n": len(must_fail),
    }


def _write(payload: dict) -> None:
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _row_brief(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": row["id"],
            "query": row.get("query"),
            "status": row.get("llm_status"),
            "error": row.get("error"),
            "reason": row.get("llm_reason"),
        }
        for row in rows
    ]


def main() -> None:
    live_before = LIVE.read_bytes() if LIVE.is_file() else b""
    t4_before = FROZEN_T4.read_bytes() if FROZEN_T4.is_file() else b""

    banned = [
        token
        for token in [
            "查一下",
            "帮我找",
            "语气",
            "修饰",
            "这一维",
            "2–4",
            "有姓",
            "姓名题",
            "inherit",
            "保单号",
            "保单",
            "对象",
            "凭证",
            "产品",
            "状态",
        ]
        if token in PRINCIPLE_T4E
    ]
    if banned:
        raise SystemExit(f"T4e principle still contains banned tokens: {banned}")

    _patch()
    spec = sim.load_project("client_search")
    runs = sim.load_runs()
    head = json.loads(HEAD_SET_B.read_text(encoding="utf-8"))
    official = json.loads(OFFICIAL_KPI.read_text(encoding="utf-8")) if OFFICIAL_KPI.is_file() else None

    needle_cases = []
    for case_id, query, pairs, _policy in T4E_NEEDLES:
        live_id = "HB009" if case_id == "HB009-needle" else case_id
        needle_cases.append(
            {
                "id": case_id,
                "query": query,
                "pairs": list(pairs),
                "extracted": _extracted_for(live_id, runs),
            }
        )

    set_b_cases = []
    set_b_catalog = []
    for item in head["cases"]:
        hid = item["id"]
        rec = runs.get(hid) or {}
        pairs = _pairs_from_live(rec)
        expected_field = item.get("expected_live_field")
        expected_fields = list(item.get("expected_live_fields") or ([expected_field] if expected_field else []))
        policy = _set_b_policy(item["class"], pairs, expected_fields)
        set_b_catalog.append((hid, item["query"], pairs, policy))
        set_b_cases.append(
            {
                "id": hid,
                "query": item["query"],
                "pairs": pairs,
                "extracted": _extracted_for(hid, runs),
                "class": item["class"],
                "policy": policy,
                "official_judge": rec.get("judge_status"),
            }
        )

    payload = {
        "note": (
            "T4e in-memory abstraction probe. Official files were not written. "
            "I007 keep-F is the project lock. Set B uses existing live extracts."
        ),
        "principle": PRINCIPLE_T4E,
        "treatment": T4E_TREATMENT,
        "banned_in_principle": banned,
        "project_lock": {
            "I007": "fulfilled",
            "not_auto_applied_to": ["I248 红莲保单", "张伟保单"],
        },
        "official_set_b": official,
        "ids": {
            "needles": [item["id"] for item in needle_cases],
            "set_b": [item["id"] for item in set_b_cases],
        },
        "llm_needles": None,
        "llm_set_b": None,
    }
    _write(payload)

    def persist_needles(rows):
        payload["llm_needles"] = {
            "treatment": T4E_TREATMENT,
            "n": len(rows),
            "ids": [row.get("id") for row in rows],
            "rows": rows,
            "score": _score(rows, T4E_NEEDLES),
        }
        _write(payload)

    def persist_set_b(rows):
        payload["llm_set_b"] = {
            "treatment": T4E_TREATMENT,
            "n": len(rows),
            "ids": [row.get("id") for row in rows],
            "rows": rows,
            "score": _score(rows, set_b_catalog),
            "vs_official": [
                {
                    "id": item["id"],
                    "query": item["query"],
                    "class": item["class"],
                    "policy": item["policy"],
                    "official_judge": item["official_judge"],
                    "t4e": next(
                        (row.get("llm_status") for row in rows if row.get("id") == item["id"]),
                        None,
                    ),
                }
                for item in set_b_cases
            ],
        }
        _write(payload)

    needle_rows = sim.run_llm_agent(
        spec,
        needle_cases,
        inject_principle=True,
        workers=4,
        persist=persist_needles,
        treatment=T4E_TREATMENT,
    )
    persist_needles(needle_rows)

    set_b_rows = sim.run_llm_agent(
        spec,
        set_b_cases,
        inject_principle=True,
        workers=4,
        persist=persist_set_b,
        treatment=T4E_TREATMENT,
    )
    persist_set_b(set_b_rows)

    if LIVE.is_file() and LIVE.read_bytes() != live_before:
        raise SystemExit("T4e wrote the live dump; abort and restore from backup")
    if FROZEN_T4.is_file() and FROZEN_T4.read_bytes() != t4_before:
        raise SystemExit("T4e wrote the frozen T4 dump; abort")

    print(
        json.dumps(
            {
                "out": str(OUT),
                "banned_in_principle": banned,
                "needles": {
                    "n": payload["llm_needles"]["n"],
                    "must_ok_n": payload["llm_needles"]["score"]["must_ok_n"],
                    "must_fail_n": payload["llm_needles"]["score"]["must_fail_n"],
                    "must_fail": [item["id"] for item in payload["llm_needles"]["score"]["must_fail"]],
                    "observe": [
                        {
                            "id": item["id"],
                            "query": item["query"],
                            "status": item["llm_status"],
                        }
                        for item in payload["llm_needles"]["score"]["observe"]
                    ],
                    "rows": _row_brief(payload["llm_needles"]["rows"]),
                },
                "set_b": {
                    "n": payload["llm_set_b"]["n"],
                    "must_ok_n": payload["llm_set_b"]["score"]["must_ok_n"],
                    "must_fail_n": payload["llm_set_b"]["score"]["must_fail_n"],
                    "must_fail": [item["id"] for item in payload["llm_set_b"]["score"]["must_fail"]],
                    "vs_official": payload["llm_set_b"]["vs_official"],
                },
                "live_unchanged": True,
                "t4_unchanged": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
