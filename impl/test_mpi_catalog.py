#!/usr/bin/env python3
"""手工检查 MPI attribute 的 source_file_catalog 是否包含 intent_prompt.py。

该文件是可执行诊断脚本，不是 pytest 测试。所有项目加载和外部仓库访问都放在
``main`` 中，避免 pytest 收集模块时产生环境相关副作用。
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path


class MockTrace:
    execution_trace = [
        {"stage": "request_normalization", "status": "ok"},
        {"stage": "intent_api_call", "status": "ok"},
        {
            "stage": "label_mapping",
            "status": "failed",
            "evidence": "intent=other",
        },
    ]
    project_fields = {"reference": {"intent": "nbev_planning"}}
    reference_contract = {}


def main() -> int:
    repository_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repository_root))

    from impl.core.project_loader import load_project
    from impl.core.schema import JudgeResult
    from impl.tools.source_retrieval import ProjectSourceFileProvider

    spec = load_project("marketting-planning-intent")
    print(f"Project: {spec.project_id}")
    source = ((spec.project.get("resources") or {}).get("source") or {})
    print(f"External repo: {source.get('repository')}")
    print()

    trace = MockTrace()
    judge_result = JudgeResult(
        trace_id="test",
        project_id="marketting-planning-intent",
        overall_fulfillment={
            "status": "not_fulfilled",
            "blocking_expectations": [
                "marketting-planning-intent:intent_contract"
            ],
        },
        reasoning_summary="label_mapping failed for the expected intent",
    )

    attribute_module = import_module(
        "impl.projects.marketting-planning-intent.attribute"
    )
    project_attribute_context = attribute_module.build_attribute_context(
        spec, trace, judge_result
    )
    print(
        "source_config_paths count: "
        f"{len(project_attribute_context.get('source_config_paths', {}))}"
    )
    print()

    provider = ProjectSourceFileProvider(spec, project_attribute_context)
    catalog = provider.list_files()

    print(f"=== Source File Catalog ({len(catalog)} files) ===")
    for index, entry in enumerate(catalog, 1):
        key = entry["key"]
        path = Path(entry["path"])
        size = entry["size_chars"]
        print(f"{index}. {key}")
        print(f"   Path: {path.name}")
        print(f"   Size: {size:,} chars")
        if "intent" in path.name.lower() or "prompt" in path.name.lower():
            print("   ⭐ INTENT/PROMPT FILE!")
        print()

    intent_prompt_found = any("intent_prompt" in entry["key"] for entry in catalog)
    print(f"✅ intent_prompt.py in catalog: {intent_prompt_found}")
    print()

    if catalog:
        first_key = catalog[0]["key"]
        print(f"=== Test reading: {first_key} ===")
        content = provider.read_file(first_key)
        if content:
            print(f"Content length: {len(content)} chars")
            print(f"First 200 chars: {content[:200]}")
        else:
            print("❌ Failed to read file")

    return 0 if intent_prompt_found else 1


if __name__ == "__main__":
    raise SystemExit(main())
