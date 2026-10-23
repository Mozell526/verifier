"""兑现：blocking 取自 blocking 轴的结果；输出字段与整体状态同 llm_probe 兑现轴（主轴 M 函数照读）。"""
from impl.core.judge import _derive_overall_status

FULFILLED = "fulfilled"


def synthesize(view):
    expectations = view.materials["result.expectations"]["expectations"]
    blocking = {i["expectation_id"]: i["blocking"] for i in view.materials["result.blocking"]["items"]}
    business = [{
        "expectation_id": e["expectation_id"], "blocking": blocking[e["expectation_id"]],
        "user_intent": e.get("about") or "", "expected_outcome": e.get("statement") or "",
        "acceptance_criteria": [{"condition": e.get("condition"), "ambiguity_group": e.get("ambiguity_group")}],
        "priority": "high" if blocking[e["expectation_id"]] else "normal",
        "evidence_refs": [{"source_refs": e.get("source_refs") or []}],
    } for e in expectations]
    assessments = [{"expectation_id": a["expectation_id"], "status": a["status"], "actual_evidence": list(a["evidence"]),
                    "downstream_impact": a["reason"], "claim_refs": list(a["claim_refs"])} for a in view.own["assessments"]]
    status = {a["expectation_id"]: a["status"] for a in assessments}
    groups = {}
    for e in expectations:
        if e.get("ambiguity_group"):
            groups.setdefault(e["ambiguity_group"], []).append(e["expectation_id"])
    for a in assessments:
        group = next((m for m in groups.values() if a["expectation_id"] in m), [])
        if a["status"] != FULFILLED and any(status.get(m) == FULFILLED for m in group):
            a["other_reading_fulfilled"] = True
    counted = [e for e in business
               if not any(a.get("other_reading_fulfilled") for a in assessments if a["expectation_id"] == e["expectation_id"])]
    overall = {"status": _derive_overall_status(counted, assessments),
               "blocking_expectations": [e["expectation_id"] for e in business if e["blocking"]]}
    statements = {e["expectation_id"]: e.get("statement") or "" for e in expectations}
    not_fulfilled = [{"expectation_id": a["expectation_id"], "statement": statements[a["expectation_id"]]}
                     for a in assessments if blocking[a["expectation_id"]] and a["status"] == "not_fulfilled"]
    return {"verdict": overall["status"], "business_expectations": business, "fulfillment_assessments": assessments,
            "overall_fulfillment": overall, "not_fulfilled": not_fulfilled,
            "claims_checked": view.materials.get("result.truthfulness") is not None,
            "reasoning_summary": view.own["reason"]}
