#!/usr/bin/env python3
"""Prefetch Bailian embeddings for rewrite variants (holdout paraphrases)."""
from __future__ import annotations
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_OUT = ROOT / ".tmp-model-channel" / "rw_query_embeddings.json"
NEED = ROOT / ".tmp-model-channel" / "need_rw_embeddings.json"

def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_dotenv(ROOT / ".env")
need = json.loads(NEED.read_text()).get("queries") or []
existing = {}
if CACHE_OUT.exists():
    existing = (json.loads(CACHE_OUT.read_text()).get("by_text") or {})
missing = [q for q in need if q not in existing]
print(f"have={len(existing)} missing={len(missing)}", flush=True)
if not missing:
    print("nothing to do", flush=True)
    raise SystemExit(0)

from impl.core.context.embedding import BailianEmbeddingProvider
provider = BailianEmbeddingProvider()
batch = 10
for i in range(0, len(missing), batch):
    chunk = missing[i:i+batch]
    t0 = time.time()
    vecs = provider.embed(chunk)
    for q, v in zip(chunk, vecs):
        existing[q] = [float(x) for x in v]
    print(f"  embed {i+len(chunk)}/{len(missing)} in {time.time()-t0:.2f}s", flush=True)
    CACHE_OUT.write_text(json.dumps({
        "provider": "bailian",
        "model": "text-embedding-v4",
        "n": len(existing),
        "by_text": existing,
    }, ensure_ascii=False))
print("DONE", CACHE_OUT, "n=", len(existing), flush=True)
