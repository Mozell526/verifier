import json
from collections import Counter, defaultdict

RESULT = "/tmp/judge-ablation-results.json"


def norm(v):
    v = str(v or "").strip()
    if v in ("F", "NF"):
        return v
    if "not_fulfilled" in v or v.startswith("NF"):
        return "NF"
    if "fulfilled" in v or v.startswith("F"):
        return "F"
    return "?"


def main():
    data = json.load(open(RESULT, encoding="utf-8"))
    if data.get("endpoint") is None:
        print("NO_RESULTS", data.get("error"))
        return
    rows = data["rows"]
    labels = data["labels"]
    cases = {c["id"]: c for c in data["cases"]}
    variants = ["current_like", "role_corrected_noisy", "evidence_tiered"]
    by = {}
    for v in variants:
        by[v] = {}
        for r in rows:
            if r["variant"] != v:
                continue
            by[v].setdefault(r["case_id"], []).append(r)

    print("ENDPOINT", data["endpoint"], data["model"])
    print("ERRORS", Counter((r["case_id"], r["variant"]) for r in rows if r["verdict"] == "ERROR"))
    print()
    header = ["id", "query", "wb", "label", "cur_s1", "cur_s2", "role_s1", "role_s2", "evi_s1", "evi_s2", "consist"]
    print("\t".join(header))
    agg = {v: {"agree_wb": 0, "agree_label": 0, "flip_f2nf": 0, "flip_nf2f": 0, "n": 0, "n_lab": 0} for v in variants}
    for cid, case in sorted(cases.items(), key=lambda kv: kv[0]):
        out = []
        for v in variants:
            rs = by[v].get(cid, [])
            v1 = norm(rs[0]["verdict"]) if len(rs) > 0 else "?"
            v2 = norm(rs[1]["verdict"]) if len(rs) > 1 else "?"
            out.append((v1, v2, v))
        wb = case["status"]
        label = "F" if cid in labels["F"] else ("NF" if cid in labels["NF"] else "")
        major = {v: (Counter([a, b]).most_common(1)[0][0] if a == b else "?") for v, (a, b, _) in [(o[2], o[0], o[1]) for o in out]}
        row = [cid, case["query"][:40], wb[:3], label]
        for _, _, v in out:
            pass
        for v in variants:
            a, b, _ = next(o for o in out if o[2] == v)
            row.append(a + "/" + b)
            if a == "?" or b == "?":
                continue
            agg[v]["n"] += 1
            m = Counter([a, b]).most_common(1)[0][0]
            if m == wb:
                agg[v]["agree_wb"] += 1
            if m == "F" and wb == "NF":
                agg[v]["flip_nf2f"] += 1
            if m == "NF" and wb == "F":
                agg[v]["flip_f2nf"] += 1
            if label:
                agg[v]["n_lab"] += 1
                if m == label:
                    agg[v]["agree_label"] += 1
        row.append("yes" if all(o[0] == o[1] and o[0] != "?" for o in out) else "no")
        print("\t".join(row))

    print()
    print("METRIC\t" + "\t".join(variants))
    for key in ("n", "agree_wb", "flip_f2nf", "flip_nf2f", "n_lab", "agree_label"):
        print(f"{key}\t" + "\t".join(str(agg[v][key]) for v in variants))
    for v in variants:
        a = agg[v]
        print(f"accuracy_label_{v}\t{round(a['agree_label'] / a['n_lab'], 3) if a['n_lab'] else 'na'}")
        print(f"agree_wb_{v}\t{round(a['agree_wb'] / a['n'], 3) if a['n'] else 'na'}")
    print()
    group = defaultdict(list)
    for r in rows:
        group[(r["case_id"], r["variant"])] = norm(r["verdict"])
    for cid in ("I128", "I342", "I499", "I517"):
        print("QUANK", cid, {v: group.get((cid, v), "?") for v in variants})


if __name__ == "__main__":
    main()
