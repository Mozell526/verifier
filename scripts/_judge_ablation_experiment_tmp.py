import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from openai import OpenAI

WORKBOOK = "/Users/xiaozijian/Downloads/verifier-client_search-cases-port8024-20260812-080210.xlsx"
OUT = "/tmp/judge-ablation-results.json"

CURATED = [
    "I003", "I006", "I040", "I041", "I048", "I051", "I075", "I078", "I089", "I101",
    "I124", "I128", "I135", "I138", "I145", "I283", "I342", "I499", "I517", "I539",
    "I597", "I607", "I669",
]
REFUSAL_TIME = ["I031", "I046", "I060", "I088", "I090", "I093", "I127", "I161"]

LABELS = {
    "F": {"I003", "I006", "I041", "I089", "I539", "I597", "I078", "I135"},
    "NF": {
        "I048", "I138", "I031", "I046", "I060", "I088", "I090", "I093", "I127",
        "I161", "I128", "I342", "I499", "I517", "I669",
    },
}

PROMPTS = {
    "current_like": (
        "你是客户搜索 Judge。判断 Live 是否完成用户请求，只输出 JSON："
        '{"verdict":"fulfilled|not_fulfilled","reason":"不超过80字"}\n'
        "规则：字段定义、操作符支持、枚举命中和确定性实现规则（enhanced_rules）都是确定性项目证据；"
        "请求精确命中实现规则时，该规则优先于一般自然语言推断。Reference 是重要辅助答案。"
    ),
    "role_corrected_noisy": (
        "你是客户搜索 Judge。判断 Live 是否完成用户请求，只输出 JSON："
        '{"verdict":"fulfilled|not_fulfilled","reason":"不超过80字"}\n'
        "先拆出用户最终想得到的客户集合及每个核心约束，再逐项比较 Live 是否完整交付。\n"
        "实现规则、matched_pattern、字段/操作符支持、合法枚举只解释 Live 如何生成或表达是否合法，"
        "不能单独证明满足用户意图。\n"
        "Reference 仅是辅助证据，冲突时以用户意图与 Live 实际交付为准。如实拒绝和透明说明不能替代核心交付。"
    ),
    "evidence_tiered": (
        "你是客户搜索 Judge。判断 Live 是否完成用户请求，只输出 JSON："
        '{"verdict":"fulfilled|not_fulfilled","reason":"不超过80字"}\n'
        "先拆出用户最终想得到的客户集合及每个核心约束，再逐项比较 Live 是否完整交付。\n"
        "实现规则、matched_pattern、字段/操作符支持、合法枚举只解释 Live 如何生成或表达是否合法，"
        "不能单独证明满足用户意图。\n"
        "Reference 仅是辅助证据，冲突时以用户意图与 Live 实际交付为准。如实拒绝和透明说明不能替代核心交付。"
    ),
}

NOISE = [
    f"field_{i} supports MATCH/CONTAINS/RANGE with enum values v{i}_1..v{i}_5; deterministic rule_{i} is active"
    for i in range(80)
]


def parse_json(v):
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v)
    except Exception:
        return {}


def load_cases():
    df = pd.read_excel(WORKBOOK, sheet_name="用例池候选区").fillna("")
    rows = [dict(r) for _, r in df.iterrows()]
    by_id = {str(r["ID"]): r for r in rows}
    selected = list(CURATED) + list(REFUSAL_TIME)
    rest = [str(r["ID"]) for r in rows if str(r["ID"]) not in set(selected)]
    rng = random.Random(20260812)
    sample = rng.sample(rest, 14)
    selected += sample
    cases = []
    for cid in selected:
        r = by_id[cid]
        inp = parse_json(r["Input / Live Request"])
        out = parse_json(r["Output / 被评估输出"])
        ref = parse_json(r["Reference"])
        cases.append(
            {
                "id": cid,
                "query": str(inp.get("user_text") or ""),
                "status": str(r["状态"]),
                "actual": {
                    "robot_text": str(out.get("robot_text") or ""),
                    "query_logic": out.get("query_logic"),
                    "matched_patterns": out.get("matched_patterns"),
                    "conditions": out.get("conditions") or [],
                },
                "reference": {
                    "robot_text": str(ref.get("robot_text") or ""),
                    "query_logic": ref.get("query_logic"),
                    "conditions": ref.get("conditions") or [],
                },
                "summary": str(r["Judge 摘要"])[:1200],
            }
        )
    return cases


def payload(case, variant):
    material = {
        "query": case["query"],
        "actual": case["actual"],
        "reference": case["reference"],
        "case_local_implementation_evidence": {
            "matched_patterns": case["actual"].get("matched_patterns"),
            "robot_text": case["actual"].get("robot_text"),
        },
    }
    if variant != "evidence_tiered":
        material["unrelated_project_implementation_evidence"] = NOISE
    return json.dumps(material, ensure_ascii=False, sort_keys=True)


def probe_endpoints():
    env = {k.strip(): v.strip() for k, v in (line.split("=", 1) for line in open(".env", encoding="utf-8") if line.strip() and not line.startswith("#") and "=" in line)}
    candidates = [
        {"name": "ainsv", "base_url": env.get("LLM_BASE_URL"), "model": env.get("LLM_MODEL"), "api_key": env.get("DEEPSEEK_API_KEY")},
        {"name": "wangshun", "base_url": env.get("LLM_FALLBACK_1_BASE_URL"), "model": env.get("LLM_FALLBACK_1_MODEL"), "api_key": env.get("LLM_FALLBACK_1_API_KEY")},
        {"name": "deepseek", "base_url": env.get("LLM_FALLBACK_2_BASE_URL"), "model": env.get("LLM_FALLBACK_2_MODEL"), "api_key": env.get("LLM_FALLBACK_2_API_KEY")},
        {"name": "web-ai-media-editor", "base_url": "https://web-ai-media-editor.cn/v1", "model": "deepseek-v4-flash", "api_key": "sk-e694199ead35590f7ccaf692e89f942ee368105bea3ccc87878d9be108c62d26"},
        {"name": "aixor", "base_url": "https://aixor.org/v1", "model": "gpt-5.6-luna", "api_key": "sk-HVgCEpTwZypFMRr40mW7PwGv9PzfabehEHbwbDuEzYqkjoiG"},
    ]
    for c in candidates:
        if not c["base_url"] or not c["api_key"]:
            continue
        try:
            client = OpenAI(api_key=c["api_key"], base_url=c["base_url"], timeout=15, max_retries=0)
            client.chat.completions.create(model=c["model"], temperature=0, max_tokens=1, messages=[{"role": "user", "content": "ping"}])
            return c
        except Exception:
            continue
    return None


def run_one(client, model, case, variant, sample):
    started = time.monotonic()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=160,
            messages=[
                {"role": "system", "content": PROMPTS[variant]},
                {"role": "user", "content": payload(case, variant)},
            ],
        )
        raw = (resp.choices[0].message.content or "").strip()
        verdict = ""
        reason = ""
        try:
            data = json.loads(raw)
            verdict = str(data.get("verdict") or "")
            reason = str(data.get("reason") or "")
        except Exception:
            verdict = raw[:80]
        norm = ""
        if "not_fulfilled" in verdict or verdict.lower().startswith("nf"):
            norm = "NF"
        elif "fulfilled" in verdict or verdict.lower().startswith("f"):
            norm = "F"
        return {
            "case_id": case["id"], "variant": variant, "sample": sample,
            "workbook": case["status"], "verdict": norm, "raw": verdict, "reason": reason,
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }
    except Exception as exc:
        return {
            "case_id": case["id"], "variant": variant, "sample": sample,
            "workbook": case["status"], "verdict": "ERROR", "raw": "",
            "reason": f"{type(exc).__name__}: {str(exc)[:160]}",
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }


def main():
    cases = load_cases()
    endpoint = probe_endpoints()
    print(json.dumps({"endpoint": endpoint and endpoint["name"], "cases": len(cases), "variants": list(PROMPTS)}, ensure_ascii=False), flush=True)
    if endpoint is None:
        json.dump({"endpoint": None, "error": "no working endpoint"}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        return
    client = OpenAI(api_key=endpoint["api_key"], base_url=endpoint["base_url"], timeout=90, max_retries=0)
    jobs = [(case, variant, sample) for case in cases for variant in PROMPTS for sample in (1, 2)]
    rows = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_one, client, endpoint["model"], *job) for job in jobs]
        for f in as_completed(futures):
            row = f.result()
            rows.append(row)
            print(json.dumps({"id": row["case_id"], "v": row["variant"], "s": row["sample"], "verdict": row["verdict"], "wb": row["workbook"], "t": row["elapsed_seconds"]}, ensure_ascii=False), flush=True)
    result = {
        "endpoint": endpoint["name"], "model": endpoint["model"],
        "cases": cases, "labels": LABELS, "prompts": PROMPTS,
        "rows": sorted(rows, key=lambda r: (r["case_id"], r["variant"], r["sample"])),
    }
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
