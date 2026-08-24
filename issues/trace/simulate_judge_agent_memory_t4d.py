"""In-memory T4d mouth. Official files are not written.

T4d keeps the same two questions as T4/T4c. It does not add example
locutions or a type table. It only states that Q1 and Q2 are independent,
and that naming something to find or hand over is still required even
when no concrete value was written.

Writes only to simulate_judge_agent_memory.t4d-extra.json.
Never overwrites the frozen t1/t2/t3/t4 dumps or the live t4 12-row dump.
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

OUT = HERE / "simulate_judge_agent_memory.t4d-extra.json"
LIVE = HERE / "simulate_judge_agent_memory.json"
FROZEN_T4 = HERE / "simulate_judge_agent_memory.t4.json"

T4D_TREATMENT = "generic_two_question_independent_q1_q2_shortcircuit_disabled"

PRINCIPLE_T4D = """
你只回答一件事：用户要的事，这次办成了没有。
对任何输入只问下面两件事。两问互相独立，谁也不能替谁回答。
不要先给问句贴类型标签。不要发明第三问。

第一问（已有字段标准）：
对这次交出来的每一个字段：如果该字段已经有标准，必须消费那条只读检查，不要另立门槛，也不要忽略它。
值跟问句写的一样，不是标准。
如果该字段本轮没有已有标准，不要发明标准，也不要因为没有标准就判这一字段失败。
第一问看的是值对不对得起该字段已经有的标准，不看用户怎么提出这次请求。
第二问看起来已经说完，不能用来跳过第一问。

第二问（整句有没有被说清）：
用户要的事以原始问句为准。摘要、改写、意图标签都不能替换问句。
把这次交出来的全部条件合在一起，对着原始问句看：点到的内容有没有对应交付。

点到：问句里出现了这次要据此查找或交出来的内容。
没点到：问句只是在发出这次请求，没有点到任何要找或要交的内容。
有没有写出可检索的具体值，不改变有没有点到。
点到了却没有对应条件，就是没说清。
不能因为没有写出具体值，就把已经点到的内容改口成不用交。
第一问过了，不能用来证明第二问过了。

先书面回答第一问，再书面回答第二问。
任一已有标准撑不住 → not_fulfilled。
点到的内容没有对应交付 → not_fulfilled。
全部已有标准都撑住，或本轮没有任何已有标准，并且点到的内容都有对应交付 → fulfilled。

交付读不到 → unclear。不要用 unclear 逃避已经能开口的情况。
不要剥词凑字段。不要为样本加例外。
不要先给问句分类再换规则。
不要因为交出来不止一个字段就判失败。
不要因为问句短就另设门槛。
不要问检索结果集会不会变。
""".strip()

# id, query, pairs, policy
# policy None = observe; same meanings as sim.LLM_POLICY
T4D_CASES = [
    ("SYN-yangjie", "杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-gongzhan", "共展", [("searchClientName", "共展")], "not_fulfilled"),
    ("I007", "张忠波保单号", [("searchClientName", "张忠波")], "not_fulfilled"),
    ("I248", "红莲保单", [("searchClientName", "红莲")], "not_fulfilled_forbidden"),
    ("SYN-help-look-yangjie", "帮忙看看杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-please-find-yangjie", "麻烦找下杨杰", [("searchClientName", "杨杰")], "fulfilled"),
    ("SYN-show-me-wangkunlin", "给我看看王坤林", [("searchClientName", "王坤林")], "fulfilled"),
    ("SYN-help-look-gongzhan", "帮忙看看共展", [("searchClientName", "共展")], "not_fulfilled"),
    ("SYN-zhangwei-policy-nameonly", "张伟保单", [("searchClientName", "张伟")], "not_fulfilled_forbidden"),
    ("SYN-zhangwei-policyno-nameonly", "张伟的保单号", [("searchClientName", "张伟")], "not_fulfilled_forbidden"),
    (
        "SYN-query-product-both",
        "查询李明的重疾险",
        [("searchClientName", "李明"), ("pCategorys", "疾病保险")],
        "fulfilled",
    ),
    ("HB009", "李明的重疾险", [("pCategorys", "疾病保险")], "not_fulfilled_forbidden"),
    (
        "SYN-lookup-clientno",
        "帮我查一下这个客户号 C000888123456",
        [("clientNo", "C000888123456")],
        "fulfilled",
    ),
    # holdout: words never written into any T4* principle
    ("SYN-holdout-please-yangjie", "劳驾查下杨杰", [("searchClientName", "杨杰")], None),
    ("SYN-holdout-please-gongzhan", "劳驾查下共展", [("searchClientName", "共展")], None),
    ("SYN-holdout-zhangwei-policy-info", "张伟保单信息", [("searchClientName", "张伟")], None),
]


def _patch() -> None:
    orig_active = sim._active_principle
    orig_q1 = sim._treatment_uses_q1

    def active(treatment: str) -> str:
        if treatment == T4D_TREATMENT:
            return PRINCIPLE_T4D
        return orig_active(treatment)

    def uses_q1(treatment: str) -> bool:
        if treatment == T4D_TREATMENT:
            return True
        return orig_q1(treatment)

    sim._active_principle = active
    sim._treatment_uses_q1 = uses_q1


def _extracted_for(case_id: str, runs: dict) -> dict | None:
    rec = runs.get(case_id) or {}
    live = rec.get("live") or {}
    extracted = live.get("extracted") if isinstance(live, dict) else None
    return extracted if isinstance(extracted, dict) else None


def _score(rows: list[dict]) -> dict:
    by_id = {row["id"]: row for row in rows}
    must_ok = []
    must_fail = []
    observe = []
    for case_id, query, _pairs, policy in T4D_CASES:
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
        elif policy == "fulfilled":
            if status == "fulfilled" and not row.get("error"):
                must_ok.append(item)
            else:
                must_fail.append(item)
        elif policy in {"not_fulfilled", "not_fulfilled_forbidden"}:
            if status == "not_fulfilled" and not row.get("error"):
                must_ok.append(item)
            else:
                must_fail.append(item)
        else:
            observe.append(item)
    return {
        "must_ok": must_ok,
        "must_fail": must_fail,
        "observe": observe,
        "must_ok_n": len(must_ok),
        "must_fail_n": len(must_fail),
    }


def _write(payload: dict) -> None:
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    live_before = LIVE.read_bytes() if LIVE.is_file() else b""
    t4_before = FROZEN_T4.read_bytes() if FROZEN_T4.is_file() else b""

    _patch()
    spec = sim.load_project("client_search")
    runs = sim.load_runs()
    cases = []
    for case_id, query, pairs, _policy in T4D_CASES:
        cases.append(
            {
                "id": case_id,
                "query": query,
                "pairs": list(pairs),
                "extracted": _extracted_for(case_id, runs),
            }
        )

    payload = {
        "note": (
            "T4d in-memory abstraction probe. Not the frozen T4 12-row score. "
            "Official files were not written."
        ),
        "principle": PRINCIPLE_T4D,
        "treatment": T4D_TREATMENT,
        "banned_in_principle": [
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
                "对象",
                "凭证",
            ]
            if token in PRINCIPLE_T4D
        ],
        "ids": [item["id"] for item in cases],
        "llm": None,
    }
    _write(payload)

    def persist(rows):
        payload["llm"] = {
            "treatment": T4D_TREATMENT,
            "n": len(rows),
            "ids": [row.get("id") for row in rows],
            "rows": rows,
            "score": _score(rows),
        }
        _write(payload)

    rows = sim.run_llm_agent(
        spec,
        cases,
        inject_principle=True,
        workers=4,
        persist=persist,
        treatment=T4D_TREATMENT,
    )
    persist(rows)

    if LIVE.is_file() and LIVE.read_bytes() != live_before:
        raise SystemExit("T4d wrote the live dump; abort and restore from backup")
    if FROZEN_T4.is_file() and FROZEN_T4.read_bytes() != t4_before:
        raise SystemExit("T4d wrote the frozen T4 dump; abort")

    print(
        json.dumps(
            {
                "out": str(OUT),
                "banned_in_principle": payload["banned_in_principle"],
                "n": payload["llm"]["n"],
                "score": {
                    "must_ok_n": payload["llm"]["score"]["must_ok_n"],
                    "must_fail_n": payload["llm"]["score"]["must_fail_n"],
                    "must_fail": [item["id"] for item in payload["llm"]["score"]["must_fail"]],
                    "observe": [
                        {
                            "id": item["id"],
                            "query": item["query"],
                            "status": item["llm_status"],
                        }
                        for item in payload["llm"]["score"]["observe"]
                    ],
                    "rows": [
                        {
                            "id": row["id"],
                            "query": row["query"],
                            "status": row.get("llm_status"),
                            "error": row.get("error"),
                        }
                        for row in payload["llm"]["rows"]
                    ],
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
