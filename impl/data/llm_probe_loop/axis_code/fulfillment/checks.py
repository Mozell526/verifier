"""兑现逐条判定的程序检查（同 llm_probe fulfillment.check_assessments，spec/alg/fulfilled.md §4）。"""


def check(view):
    truth = view.materials.get("result.truthfulness")
    claims = truth["claims"] if truth else None
    by_id = {c["claim_id"]: c for c in claims or []}
    problems = []
    for item in view.own["assessments"]:
        key, status, refs = item["expectation_id"], item["status"], item["claim_refs"]
        unknown = [r for r in refs if r not in by_id]
        if unknown:
            problems.append(f"{key}：claim_refs {unknown} 不在核事实结果里" if claims is not None
                            else f"{key}：没有核事实结果，claim_refs 必须为空")
        cited = [by_id[r] for r in refs if r in by_id]
        if any(c["verdict"] == "refuted" for c in cited) and status != "not_fulfilled":
            problems.append(f"{key}：引用了 refuted 的 claim，status 必须是 not_fulfilled")
        if status == "fulfilled":
            unverified = [c["claim_id"] for c in cited if c["verdict"] == "unverifiable"
                          and not (c.get("qualifies") and (by_id.get(c["qualifies"]) or {}).get("verdict") == "verified")]
            if unverified:
                problems.append(f"{key}：引用的 claim {unverified} 核实不了，不能判 fulfilled")
            if claims is not None and not any(c["verdict"] == "verified" for c in cited):
                problems.append(f"{key}：有核事实结果时，fulfilled 必须引用至少一条 verified 的 claim")
    return problems
