"""对多轮 T1 请求 live parse，用真实 message 填 last-turn assistant。"""
from __future__ import annotations

import json
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from impl.core.project_loader import load_project
from impl.projects.policy_search.live import PolicySearchLive
from impl.projects.policy_search.rich_mock import _HANDWRITTEN_MULTITURN

ROOT = Path(__file__).resolve().parents[4]
CACHE_PATH = ROOT / "impl" / "data" / "policy_search" / "context_prior_live.json"
PARSE_URL = "http://127.0.0.1:8050/api/v1/policy-search/policy-search-parse"


def _request_body(query: str) -> dict:
    request_id = uuid.uuid4().hex
    return {
        "session_id": f"verifier-prior-{request_id[:12]}",
        "trace_id": f"verifier-prior-{request_id}",
        "user_id": "verifier-user",
        "org_id": "verifier-org",
        "org_name": "verifier",
        "ts": 1785983400000,
        "token": "",
        "app_scenario": "policy_search_parse",
        "source": "verifier",
        "user_text": "",
        "history": [],
        "user_action": "write",
        "action_scenario": "policySearch",
        "extra_input_params": {
            "policySearchParseArgs": {
                "query": query,
                "currentTime": "2026-08-06 10:30:00",
                "agentCode": "A12345678",
            },
            "agent_args": None,
            "args": {"contexts": []},
        },
        "application_setting": None,
        "scenario": None,
    }


def fetch_prior(query: str, live: PolicySearchLive) -> dict[str, str]:
    body = json.dumps(_request_body(query), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        PARSE_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = json.loads(response.read().decode("utf-8"))
    extracted = live.extract_output([raw])
    message = str(extracted.get("message") or "").strip()
    status = str(extracted.get("status") or "").strip()
    if not message:
        raise ValueError(f"live prior returned empty message: {query!r} status={status}")
    return {"query": query, "status": status, "message": message}


def main() -> int:
    live = PolicySearchLive(load_project("policy_search"))
    queries = list(dict.fromkeys(previous for _id, _scenario, _intent, previous, _current in _HANDWRITTEN_MULTITURN))
    cache: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(fetch_prior, query, live): query for query in queries}
        for fut in as_completed(futs):
            query = futs[fut]
            try:
                cache[query] = fut.result()
                print(f"{cache[query]['status']}\t{query}\t{cache[query]['message']}", flush=True)
            except Exception as exc:
                errors.append(f"{query}: {exc}")
                print(f"FAIL\t{query}\t{exc}", flush=True)
    if errors:
        raise SystemExit("live prior fetch failed:\n" + "\n".join(errors))
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "cache": str(CACHE_PATH),
        "prior_count": len(cache),
        "status_counts": dict(Counter(item["status"] for item in cache.values())),
        "unique_messages": len({item["message"] for item in cache.values()}),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
