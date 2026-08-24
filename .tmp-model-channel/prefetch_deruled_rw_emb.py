#!/usr/bin/env python3
"""Embed deruled rewrite variants (run on verifier machine)."""
from __future__ import annotations
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "experiments" / "model-channel-cache"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    for p in [Path.cwd() / ".env", Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/.env")]:
        load_dotenv(p)
    rw_path = CACHE / "llm_rewrites_deruled.json"
    q_path = CACHE / "query_embeddings.json"
    out_path = CACHE / "rw_query_embeddings_deruled.json"
    rw = json.loads(rw_path.read_text()) if rw_path.exists() else {}
    q_existing = (json.loads(q_path.read_text()).get("by_text") or {}) if q_path.exists() else {}
    existing = (json.loads(out_path.read_text()).get("by_text") or {}) if out_path.exists() else {}
    need, seen = [], set()
    for arr in (rw.get("by_text") or {}).values():
        for v in arr or []:
            if not v or v in seen:
                continue
            seen.add(v)
            if v not in existing and v not in q_existing:
                need.append(v)
    print(f"need={len(need)} have={len(existing)} q={len(q_existing)}", flush=True)
    if not need:
        return
    import sys
    sys.path.insert(0, str(Path.cwd()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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
        out_path.write_text(json.dumps({"provider": "bailian", "model": "text-embedding-v4", "n": len(existing), "by_text": existing}, ensure_ascii=False))
    print("done n", len(existing), flush=True)


if __name__ == "__main__":
    main()
