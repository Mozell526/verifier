#!/usr/bin/env python3
"""Prefetch NEW deruled rewrite+plan LLM caches (do not overwrite old Prefer-routing caches).

Run on verifier machine:
  bash run.sh python /path/to/prefetch_deruled_cache.py

Writes (alongside existing caches):
  experiments/model-channel-cache/llm_rewrites_deruled.json
  experiments/model-channel-cache/llm_plans_deruled.json
  experiments/model-channel-cache/rw_query_embeddings_deruled.json
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "experiments" / "model-channel-cache"
CACHE.mkdir(parents=True, exist_ok=True)
LIST = CACHE / "query_list.json"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


REWRITE_SYS = (
    "You rewrite catalog search queries for a multi-collection business key-index "
    "(fields / rules / spoken mappings / abbr enums). "
    "Return ONLY a JSON array of 1-3 short Chinese keyword variants. "
    "Hard rules: variants MUST be splits or reorders of tokens already present in the query; "
    "do NOT add new entities, grades, product names, or implied synonyms; "
    "do not invent database field ids; do not paste holdout gold answers; "
    "do not add English field paths; keep only characters/tokens that appear in the original query."
)

PLAN_SYS = (
    "You are an Investigate navigator over Catalog indexes. Collections: "
    "field (business field definitions), enhanced_rules, value_mappings (spoken keys), abbrname (enum members). "
    "Return ONLY one JSON object: "
    '{"collections":["field",...],"rewrite":null|string,"stop_if_empty":bool,'
    '"chitchat_confident":bool,"reason":"..."} '
    "Default: search ALL registered Catalog indexes "
    '["field","enhanced_rules","value_mappings","abbrname"]. '
    "Do NOT prefer-route (do not send proper names only to abbr, attributes only to field, "
    "campaigns only to rules). "
    "collections:[] ONLY if you are highly confident the query is chitchat/irrelevant "
    "AND set chitchat_confident=true. If unsure, return all collections. "
    "Do not invent case-specific business reject lists."
)


def llm_call(messages, *, max_tokens=900, temperature=0.0):
    trials = [
        (
            os.environ.get("LLM_FALLBACK_1_BASE_URL"),
            os.environ.get("LLM_FALLBACK_1_MODEL"),
            os.environ.get("LLM_FALLBACK_1_API_KEY"),
        ),
        (
            os.environ.get("LLM_FALLBACK_2_BASE_URL"),
            os.environ.get("LLM_FALLBACK_2_MODEL"),
            os.environ.get("LLM_FALLBACK_2_API_KEY"),
        ),
        (
            os.environ.get("LLM_BASE_URL"),
            os.environ.get("LLM_MODEL"),
            os.environ.get("DEEPSEEK_API_KEY"),
        ),
    ]
    last = None
    for base, model, key in trials:
        if not (base and model and key):
            continue
        url = base.rstrip("/") + "/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        )
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if not content:
                content = (msg.get("reasoning_content") or "").strip()
            meta = {
                "model": model,
                "base": base,
                "latency_s": round(time.time() - t0, 3),
                "usage": data.get("usage") or {},
                "finish_reason": data["choices"][0].get("finish_reason"),
            }
            return content, meta
        except Exception as e:
            last = f"{model}@{base}: {type(e).__name__}: {e}"
            continue
    raise RuntimeError(last or "no LLM endpoint")


def extract_json_array(text: str) -> list[str]:
    if not text:
        return []
    candidates = re.findall(r"\[[\s\S]*?\]", text)
    for c in reversed(candidates):
        try:
            arr = json.loads(c)
            if isinstance(arr, list):
                out = []
                for x in arr:
                    if isinstance(x, str) and x.strip():
                        out.append(x.strip())
                    elif isinstance(x, dict) and x.get("query"):
                        out.append(str(x["query"]).strip())
                if out:
                    return out[:3]
        except Exception:
            continue
    return []


def extract_json_obj(text: str) -> dict:
    if not text:
        return {}
    candidates = re.findall(r"\{[\s\S]*?\}", text)
    for c in reversed(candidates):
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {}


def is_ultra_short_query(query: str) -> bool:
    q = str(query or "").strip()
    if not q:
        return True
    if len(q) <= 2:
        return True
    if re.fullmatch(r"[A-Za-z]+", q) and len(q) <= 2:
        return True
    return False


def prefetch_rewrites(queries: list[str]) -> dict:
    out_path = CACHE / "llm_rewrites_deruled.json"
    existing = {}
    meta_all = {}
    if out_path.exists():
        doc = json.loads(out_path.read_text())
        existing = doc.get("by_text") or {}
        meta_all = doc.get("meta_by_text") or {}
    missing = [q for q in queries if q not in existing]
    print(f"deruled rewrites: have={len(existing)} missing={len(missing)}", flush=True)
    errors = 0
    skipped = 0
    for i, q in enumerate(missing):
        if is_ultra_short_query(q):
            existing[q] = []
            meta_all[q] = {"skipped": True, "skip_reason": "ultra_short_query"}
            skipped += 1
            continue
        try:
            content, meta = llm_call(
                [
                    {"role": "system", "content": REWRITE_SYS},
                    {"role": "user", "content": f"Query: {q}"},
                ]
            )
            arr = extract_json_array(content)
            if not arr:
                arr = []
                meta["parse_fallback"] = True
            existing[q] = arr
            meta_all[q] = meta
        except Exception as e:
            errors += 1
            existing[q] = []
            meta_all[q] = {"error": str(e)}
            print(f"  rewrite fail {i}: {e}", flush=True)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  rewrite {i+1}/{len(missing)} errors={errors} skipped_so_far={skipped}", flush=True)
            out_path.write_text(
                json.dumps(
                    {
                        "prompt_id": "deruled_rewrite_v1",
                        "by_text": existing,
                        "meta_by_text": meta_all,
                        "n": len(existing),
                        "errors": errors,
                    },
                    ensure_ascii=False,
                )
            )
    out_path.write_text(
        json.dumps(
            {
                "prompt_id": "deruled_rewrite_v1",
                "by_text": existing,
                "meta_by_text": meta_all,
                "n": len(existing),
                "errors": errors,
                "skipped_ultrashort": skipped,
            },
            ensure_ascii=False,
        )
    )
    return {"ok": errors == 0, "n": len(existing), "errors": errors, "path": str(out_path)}


def prefetch_plans(queries: list[str]) -> dict:
    out_path = CACHE / "llm_plans_deruled.json"
    existing = {}
    meta_all = {}
    if out_path.exists():
        doc = json.loads(out_path.read_text())
        existing = doc.get("by_text") or {}
        meta_all = doc.get("meta_by_text") or {}
    missing = [q for q in queries if q not in existing]
    print(f"deruled plans: have={len(existing)} missing={len(missing)}", flush=True)
    errors = 0
    allowed = {"field", "enhanced_rules", "value_mappings", "abbrname"}
    default_cols = ["field", "enhanced_rules", "value_mappings", "abbrname"]
    for i, q in enumerate(missing):
        try:
            content, meta = llm_call(
                [
                    {"role": "system", "content": PLAN_SYS},
                    {"role": "user", "content": f"Query: {q}"},
                ],
                max_tokens=700,
            )
            obj = extract_json_obj(content)
            if not obj:
                obj = {
                    "collections": list(default_cols),
                    "rewrite": None,
                    "stop_if_empty": False,
                    "chitchat_confident": False,
                    "reason": "parse_fallback_all_catalog",
                }
                meta["parse_fallback"] = True
            cols = [c for c in (obj.get("collections") or []) if c in allowed]
            obj["collections"] = cols
            existing[q] = obj
            meta_all[q] = meta
        except Exception as e:
            errors += 1
            existing[q] = {
                "collections": list(default_cols),
                "rewrite": None,
                "stop_if_empty": False,
                "chitchat_confident": False,
                "reason": f"error:{e}",
            }
            meta_all[q] = {"error": str(e)}
            print(f"  plan fail {i}: {e}", flush=True)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  plan {i+1}/{len(missing)} errors={errors}", flush=True)
            out_path.write_text(
                json.dumps(
                    {
                        "prompt_id": "deruled_plan_v1",
                        "by_text": existing,
                        "meta_by_text": meta_all,
                        "n": len(existing),
                        "errors": errors,
                    },
                    ensure_ascii=False,
                )
            )
    out_path.write_text(
        json.dumps(
            {
                "prompt_id": "deruled_plan_v1",
                "by_text": existing,
                "meta_by_text": meta_all,
                "n": len(existing),
                "errors": errors,
            },
            ensure_ascii=False,
        )
    )
    return {"ok": errors == 0, "n": len(existing), "errors": errors, "path": str(out_path)}


def prefetch_variant_embeddings(rewrite_doc: dict) -> dict:
    out_path = CACHE / "rw_query_embeddings_deruled.json"
    q_path = CACHE / "query_embeddings.json"
    existing = {}
    if out_path.exists():
        existing = json.loads(out_path.read_text()).get("by_text") or {}
    q_existing = {}
    if q_path.exists():
        q_existing = json.loads(q_path.read_text()).get("by_text") or {}
    need = []
    seen = set()
    for arr in (rewrite_doc.get("by_text") or {}).values():
        for v in arr or []:
            if not v or v in seen:
                continue
            seen.add(v)
            if v not in existing and v not in q_existing:
                need.append(v)
    print(f"deruled rw-emb: have={len(existing)} also_in_q={len(q_existing)} missing={len(need)}", flush=True)
    if not need:
        if not out_path.exists():
            out_path.write_text(json.dumps({"provider": "bailian", "n": 0, "by_text": existing}, ensure_ascii=False))
        return {"ok": True, "n": len(existing), "missing": 0, "path": str(out_path)}
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path.cwd()))
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from impl.core.context.embedding import BailianEmbeddingProvider

        provider = BailianEmbeddingProvider()
        batch = 10
        for i in range(0, len(need), batch):
            chunk = need[i : i + batch]
            t0 = time.time()
            vecs = provider.embed(chunk)
            for q, v in zip(chunk, vecs):
                existing[q] = [float(x) for x in v]
            print(f"  embed {i+len(chunk)}/{len(need)} in {time.time()-t0:.2f}s", flush=True)
            out_path.write_text(
                json.dumps(
                    {
                        "provider": "bailian",
                        "model": "text-embedding-v4",
                        "n": len(existing),
                        "by_text": existing,
                    },
                    ensure_ascii=False,
                )
            )
        return {"ok": True, "n": len(existing), "missing": 0, "path": str(out_path)}
    except Exception as e:
        print(f"EMBED_BLOCKER: {type(e).__name__}: {e}", flush=True)
        out_path.write_text(
            json.dumps({"provider": None, "error": str(e), "by_text": existing}, ensure_ascii=False)
        )
        return {"ok": False, "error": str(e), "n": len(existing), "missing": len(need)}


def main():
    for p in [
        Path.cwd() / ".env",
        Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/.env"),
    ]:
        load_dotenv(p)
    if not LIST.exists():
        raise SystemExit(f"missing {LIST}")
    doc = json.loads(LIST.read_text())
    queries = [x["query"] if isinstance(x, dict) else str(x) for x in doc["queries"]]
    plan_qs = list(doc.get("plan_queries") or [])
    print("unique queries", len(queries), "plan_queries", len(plan_qs), flush=True)
    rw = prefetch_rewrites(queries)
    print("rw", rw, flush=True)
    pl = prefetch_plans(plan_qs)
    print("plans", pl, flush=True)
    rw_doc = json.loads((CACHE / "llm_rewrites_deruled.json").read_text()) if (CACHE / "llm_rewrites_deruled.json").exists() else {}
    emb = prefetch_variant_embeddings(rw_doc)
    print("emb", emb, flush=True)
    summary = {"rewrites": rw, "plans": pl, "rw_embeddings": emb, "n_queries": len(queries)}
    (CACHE / "prefetch_deruled_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
