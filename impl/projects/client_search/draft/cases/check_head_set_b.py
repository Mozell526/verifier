from __future__ import annotations

import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
SET_B = HERE / "head_set_b.json"
SET_A = HERE / "set_a_badcase_queries.json"
BARE_NAME = re.compile(r"^[\u4e00-\u9fff]{2,4}$")
CLIENT_OR_POL = re.compile(r"[CPCAcp][A-Za-z0-9]{8,}")
ALLOWED_CLASSES = {"bare_name", "name_plus_product", "legal_id"}


def main() -> int:
    set_b = json.loads(SET_B.read_text(encoding="utf-8"))
    set_a = json.loads(SET_A.read_text(encoding="utf-8"))
    cases = set_b["cases"]
    set_a_queries = {str(item["query"]).strip() for item in set_a["queries"] if item.get("query")}
    queries = [str(case["query"]).strip() for case in cases]
    errors: list[str] = []

    if not set_b.get("frozen"):
        errors.append("set B must be frozen")
    if set_b.get("source") != "constructed_independent":
        errors.append("set B must be independently constructed")
    if set_b.get("policy", {}).get("name_morphology_alone_can_fulfill") is not True:
        errors.append("policy 1A missing: name morphology must be allowed to fulfill")
    if {case["class"] for case in cases} != ALLOWED_CLASSES:
        errors.append(f"set B classes must be exactly {sorted(ALLOWED_CLASSES)}")
    if len(queries) != len(set(queries)):
        errors.append("set B queries must be unique")

    overlap = sorted(set(queries) & set_a_queries)
    if overlap:
        errors.append(f"set B overlaps set A: {overlap}")

    for case in cases:
        case_id = case["id"]
        query = str(case["query"]).strip()
        klass = case["class"]
        if case.get("expected_status") != "fulfilled":
            errors.append(f"{case_id}: expected_status must be fulfilled")
        if klass not in ALLOWED_CLASSES:
            errors.append(f"{case_id}: unknown class {klass}")
        if klass == "bare_name" and not BARE_NAME.fullmatch(query):
            errors.append(f"{case_id}: bare_name must be 2-4 Chinese characters")
        if klass == "name_plus_product" and BARE_NAME.fullmatch(query):
            errors.append(f"{case_id}: name_plus_product must not be a bare name")
        if klass == "legal_id" and not CLIENT_OR_POL.search(query):
            errors.append(f"{case_id}: legal_id must contain a well-formed id")

    if errors:
        raise SystemExit("\n".join(errors))
    print(
        json.dumps(
            {
                "ok": True,
                "set_b": set_b["id"],
                "n": len(cases),
                "classes": {
                    klass: sum(1 for case in cases if case["class"] == klass)
                    for klass in sorted(ALLOWED_CLASSES)
                },
                "overlap_with_set_a": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
