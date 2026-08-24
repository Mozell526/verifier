import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI


def parse_env(path):
    env = {}
    if not os.path.exists(path):
        return env
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def probe(c):
    if not c["base_url"] or not c["api_key"]:
        return {**c, "ok": False, "error": "missing config"}
    started = time.monotonic()
    try:
        client = OpenAI(api_key=c["api_key"], base_url=c["base_url"], timeout=20, max_retries=0)
        resp = client.chat.completions.create(
            model=c["model"],
            temperature=0,
            max_tokens=3,
            messages=[{"role": "user", "content": "ping"}],
        )
        content = resp.choices[0].message.content or ""
        return {**c, "ok": True, "elapsed": round(time.monotonic() - started, 2), "reply": content[:60]}
    except Exception as exc:
        return {**c, "ok": False, "elapsed": round(time.monotonic() - started, 2), "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def main():
    env = parse_env(".env")
    candidates = [
        {"name": "ainsv", "base_url": env.get("LLM_BASE_URL"), "model": env.get("LLM_MODEL"), "api_key": env.get("DEEPSEEK_API_KEY")},
        {"name": "wangshun", "base_url": env.get("LLM_FALLBACK_1_BASE_URL"), "model": env.get("LLM_FALLBACK_1_MODEL"), "api_key": env.get("LLM_FALLBACK_1_API_KEY")},
        {"name": "deepseek", "base_url": env.get("LLM_FALLBACK_2_BASE_URL"), "model": env.get("LLM_FALLBACK_2_MODEL"), "api_key": env.get("LLM_FALLBACK_2_API_KEY")},
        {"name": "web-ai-media-editor", "base_url": "https://web-ai-media-editor.cn/v1", "model": "deepseek-v4-flash", "api_key": "sk-e694199ead35590f7ccaf692e89f942ee368105bea3ccc87878d9be108c62d26"},
        {"name": "aixor", "base_url": "https://aixor.org/v1", "model": "gpt-5.6-luna", "api_key": "sk-HVgCEpTwZypFMRr40mW7PwGv9PzfabehEHbwbDuEzYqkjoiG"},
    ]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(probe, c) for c in candidates]
        for f in as_completed(futures):
            r = f.result()
            print(json.dumps({"name": r["name"], "ok": r["ok"], "elapsed": r.get("elapsed"), "model": r["model"], "error": r.get("error"), "reply": r.get("reply")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
