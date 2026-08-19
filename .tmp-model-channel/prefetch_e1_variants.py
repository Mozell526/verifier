#!/usr/bin/env python3
"""Embed E1-passing query-internal variants that lack vectors. Run on verifier machine."""
from __future__ import annotations
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# support both box-style and .tmp-model-channel layouts
CANDIDATE_CACHE = [
    ROOT / "experiments" / "model-channel-cache",
    ROOT / ".tmp-model-channel" / "experiments" / "model-channel-cache",
    Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/.tmp-model-channel/experiments/model-channel-cache"),
]
NEED_CANDIDATES = [
    ROOT / "experiments" / "model-channel-cache" / "need_e1_embeddings.json",
    ROOT / "need_e1_embeddings.json",
    Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/.tmp-model-channel/need_e1_embeddings.json"),
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    for p in [
        Path.cwd() / ".env",
        Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/.env"),
    ]:
        load_dotenv(p)
    cache = next((p for p in CANDIDATE_CACHE if p.exists()), CANDIDATE_CACHE[0])
    need_path = next((p for p in NEED_CANDIDATES if p.exists()), None)
    if need_path is None:
        raise SystemExit("need_e1_embeddings.json not found")
    need = json.loads(need_path.read_text()).get("queries") or []
    q_path = cache / "query_embeddings.json"
    out_path = cache / "rw_query_embeddings_deruled.json"
    q_existing = (json.loads(q_path.read_text()).get("by_text") or {}) if q_path.exists() else {}
    existing = (json.loads(out_path.read_text()).get("by_text") or {}) if out_path.exists() else {}
    todo = [v for v in need if v and v not in existing and v not in q_existing]
    print(f"cache={cache} need={len(need)} todo={len(todo)} have_rw={len(existing)} q={len(q_existing)}", flush=True)
    if not todo:
        print("nothing to embed", flush=True)
        return
    import sys
    sys.path.insert(0, str(Path("/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier")))
    sys.path.insert(0, str(Path.cwd()))
    from impl.core.context.embedding import BailianEmbeddingProvider
    provider = BailianEmbeddingProvider()
    batch = 10
    for i in range(0, len(todo), batch):
        chunk = todo[i : i + batch]
        t0 = time.time()
        vecs = provider.embed(chunk)
        for q, v in zip(chunk, vecs):
            existing[q] = [float(x) for x in v]
        print(f"  embed {i+len(chunk)}/{len(todo)} in {time.time()-t0:.2f}s", flush=True)
        out_path.write_text(
            json.dumps(
                {"provider": "bailian", "model": "text-embedding-v4", "n": len(existing), "by_text": existing},
                ensure_ascii=False,
            )
        )
    print("done n", len(existing), "out", out_path, flush=True)


if __name__ == "__main__":
    main()
