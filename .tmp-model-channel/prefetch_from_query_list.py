#!/usr/bin/env python3
"""Standalone prefetch using query_list.json (no draft-run imports)."""
from __future__ import annotations

import sys
from pathlib import Path as _P
_VER=_P(__file__).resolve().parents[1]
if str(_VER) not in sys.path:
    sys.path.insert(0, str(_VER))

import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "experiments" / "model-channel-cache"
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
    "Rules: do not invent database field ids; do not paste holdout gold answers; "
    "do not add English field paths; keep variants faithful to the user intent; "
    "prefer nouns/phrases present or strongly implied by the query."
)
PLAN_SYS = (
    "You are an Investigate navigator over Catalog indexes. Collections: "
    "field (business field definitions), enhanced_rules, value_mappings (spoken keys), abbrname (enum members). "
    "Return ONLY one JSON object: "
    '{"collections":["field",...],"rewrite":null|string,"stop_if_empty":bool,"reason":"..."} '
    "Choose 1-3 collections. Prefer abbrname/value_mappings for short proper-name/code queries; "
    "field for attribute nouns; enhanced_rules for campaign/rule names. "
    "For clearly irrelevant/chitchat queries, return collections:[]. "
    "Do not invent case-specific business reject lists."
)


def llm_call(messages, *, max_tokens=900, temperature=0.0):
    trials = [
        (os.environ.get("LLM_FALLBACK_1_BASE_URL"), os.environ.get("LLM_FALLBACK_1_MODEL"), os.environ.get("LLM_FALLBACK_1_API_KEY")),
        (os.environ.get("LLM_FALLBACK_2_BASE_URL"), os.environ.get("LLM_FALLBACK_2_MODEL"), os.environ.get("LLM_FALLBACK_2_API_KEY")),
        (os.environ.get("LLM_BASE_URL"), os.environ.get("LLM_MODEL"), os.environ.get("DEEPSEEK_API_KEY")),
    ]
    last = None
    for base, model, key in trials:
        if not (base and model and key):
            continue
        url = base.rstrip("/") + "/chat/completions"
        body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}
        )
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()
            meta = {
                "model": model,
                "base": base,
                "latency_s": round(time.time() - t0, 3),
                "usage": data.get("usage") or {},
                "finish_reason": data["choices"][0].get("finish_reason"),
            }
            return content, meta
        except Exception as e:
            last = f"{model}: {type(e).__name__}: {e}"
    raise RuntimeError(last or "no LLM")


def extract_json_array(text: str):
    for c in reversed(re.findall(r"\[[\s\S]*?\]", text or "")):
        try:
            arr = json.loads(c)
            if isinstance(arr, list):
                out = [str(x).strip() for x in arr if isinstance(x, str) and x.strip()]
                if out:
                    return out[:3]
        except Exception:
            pass
    return []


def extract_json_obj(text: str):
    for c in reversed(re.findall(r"\{[\s\S]*?\}", text or "")):
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {}


def main():
    for p in [Path.cwd() / ".env", Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/.env")]:
        load_dotenv(p)
    doc = json.loads(LIST.read_text())
    queries = [x["query"] for x in doc["queries"]]
    plan_queries = list(doc.get("plan_queries") or [])
    print("queries", len(queries), "plans", len(plan_queries), flush=True)

    # embeddings
    emb_path = CACHE / "query_embeddings.json"
    by_text = {}
    if emb_path.exists():
        by_text = json.loads(emb_path.read_text()).get("by_text") or {}
    missing = [q for q in queries if q not in by_text]
    print("embed missing", len(missing), flush=True)
    if missing:
        from impl.core.context.embedding import BailianEmbeddingProvider

        provider = BailianEmbeddingProvider()
        for i in range(0, len(missing), 10):
            chunk = missing[i : i + 10]
            t0 = time.time()
            vecs = provider.embed(chunk)
            for q, v in zip(chunk, vecs):
                by_text[q] = [float(x) for x in v]
            print(f"embed {i+len(chunk)}/{len(missing)} {time.time()-t0:.2f}s", flush=True)
            emb_path.write_text(json.dumps({"provider": "bailian", "model": "text-embedding-v4", "n": len(by_text), "by_text": by_text}, ensure_ascii=False))
    emb_path.write_text(json.dumps({"provider": "bailian", "model": "text-embedding-v4", "n": len(by_text), "by_text": by_text}, ensure_ascii=False))

    # rewrites
    rw_path = CACHE / "llm_rewrites.json"
    rw = {}
    rw_meta = {}
    if rw_path.exists():
        d = json.loads(rw_path.read_text())
        rw = d.get("by_text") or {}
        rw_meta = d.get("meta_by_text") or {}
    missing = [q for q in queries if q not in rw]
    print("rewrite missing", len(missing), flush=True)
    errors = 0
    for i, q in enumerate(missing):
        try:
            content, meta = llm_call([{"role": "system", "content": REWRITE_SYS}, {"role": "user", "content": f"Query: {q}"}])
            arr = extract_json_array(content) or [q]
            rw[q] = arr
            rw_meta[q] = meta
        except Exception as e:
            errors += 1
            rw[q] = []
            rw_meta[q] = {"error": str(e)}
            print("rw fail", i, e, flush=True)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"rw {i+1}/{len(missing)}", flush=True)
            rw_path.write_text(json.dumps({"by_text": rw, "meta_by_text": rw_meta, "n": len(rw), "errors": errors}, ensure_ascii=False))
    rw_path.write_text(json.dumps({"by_text": rw, "meta_by_text": rw_meta, "n": len(rw), "errors": errors}, ensure_ascii=False))

    # plans
    pl_path = CACHE / "llm_plans.json"
    pl = {}
    pl_meta = {}
    if pl_path.exists():
        d = json.loads(pl_path.read_text())
        pl = d.get("by_text") or {}
        pl_meta = d.get("meta_by_text") or {}
    missing = [q for q in plan_queries if q not in pl]
    print("plan missing", len(missing), flush=True)
    errors = 0
    allowed = {"field", "enhanced_rules", "value_mappings", "abbrname"}
    for i, q in enumerate(missing):
        try:
            content, meta = llm_call(
                [{"role": "system", "content": PLAN_SYS}, {"role": "user", "content": f"Query: {q}"}],
                max_tokens=700,
            )
            obj = extract_json_obj(content) or {
                "collections": ["field", "enhanced_rules"],
                "rewrite": None,
                "stop_if_empty": True,
                "reason": "parse_fallback",
            }
            obj["collections"] = [c for c in (obj.get("collections") or []) if c in allowed]
            pl[q] = obj
            pl_meta[q] = meta
        except Exception as e:
            errors += 1
            pl[q] = {
                "collections": ["field", "enhanced_rules", "value_mappings", "abbrname"],
                "rewrite": None,
                "stop_if_empty": False,
                "reason": f"error:{e}",
            }
            pl_meta[q] = {"error": str(e)}
            print("plan fail", i, e, flush=True)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"plan {i+1}/{len(missing)}", flush=True)
            pl_path.write_text(json.dumps({"by_text": pl, "meta_by_text": pl_meta, "n": len(pl), "errors": errors}, ensure_ascii=False))
    pl_path.write_text(json.dumps({"by_text": pl, "meta_by_text": pl_meta, "n": len(pl), "errors": errors}, ensure_ascii=False))
    print("DONE emb", len(by_text), "rw", len(rw), "pl", len(pl), flush=True)


if __name__ == "__main__":
    main()
