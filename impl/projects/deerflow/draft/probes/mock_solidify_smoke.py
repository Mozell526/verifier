#!/usr/bin/env python3
"""Generate one candidate DeerFlow Mock sample for every investigation demand space."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from impl.core.context.project import role_asset_context_records
from impl.core.project_loader import load_adapter, load_project, load_project_role_instance
from impl.core.solidify import write_solidify_probe_result
from impl.projects.deerflow.draft.tools.mock_validation_tools import (
    build_mock_business_input_validate_tool,
)


_SCENARIOS = {
    "open-world-nbev-work": "single_turn_planning",
    "continue-or-adjust-existing-work": "multi_turn_dimension_accumulation",
    "clarification-and-ambiguity": "clarification",
    "authorization-or-domain-boundary": "authorization_boundary",
}
_FORBIDDEN_USER_LANGUAGE = re.compile(
    r"judge|verifier|evaluation|mock\s*agent|prompt|system[_ ]?prompt|"
    r"thread_id|trace_id|org_id|user_id|json|http|api|端口|"
    r"[/\\][\w.-]+[/\\]|\.(?:py|md|json|yaml)\b|仓库|源码",
    re.IGNORECASE,
)


def run() -> dict[str, Any]:
    spec = load_project("deerflow")
    records = role_asset_context_records(
        spec,
        role="mock",
        use_candidate=True,
        require_available=True,
    )
    contract_records = [
        record for record in records if record.unit_type == "mock_investigation_contract"
    ]
    if len(contract_records) != 1:
        raise AssertionError(
            "candidate DeerFlow Mock must expose exactly one investigation contract ContextUnit"
        )

    role = load_project_role_instance(spec, "mock", load_adapter(spec))
    if role is None:
        raise AssertionError("candidate DeerFlow Mock did not instantiate")
    contract = role._contract()
    declared_spaces = {
        str(item.get("space_id") or "") for item in contract.get("demand_spaces") or []
    }
    if declared_spaces != set(_SCENARIOS):
        raise AssertionError(
            "smoke scenarios do not cover declared DeerFlow demand spaces: "
            f"{sorted(declared_spaces)}"
        )

    validator = build_mock_business_input_validate_tool()
    samples: list[dict[str, Any]] = []
    for demand_space_id, scenario in _SCENARIOS.items():
        intent = role.build_user_intent_for_case(scenario)
        query = str(getattr(intent, "query", "") or "").strip()
        user_intent = str(getattr(intent, "user_intent", "") or "").strip()
        if not query or not user_intent:
            raise AssertionError(
                f"candidate DeerFlow Mock produced an empty sample for {demand_space_id}"
            )
        if _FORBIDDEN_USER_LANGUAGE.search(query):
            raise AssertionError(
                "candidate DeerFlow Mock leaked evaluator/system language for "
                f"{demand_space_id}: {query}"
            )
        selected = role._select_demand_space(contract, scenario)
        if selected.get("space_id") != demand_space_id:
            raise AssertionError(
                f"scenario {scenario} selected {selected.get('space_id')}, "
                f"expected {demand_space_id}"
            )
        request = role.build_initial_request(intent)
        message = str(
            (((request.get("input") or {}).get("messages") or [{}])[-1]).get("content")
            or ""
        ).strip()
        if message != query:
            raise AssertionError(
                "candidate DeerFlow Mock did not preserve generated user language"
            )
        serialized = {
            "scenario": scenario,
            "user_intent": user_intent,
            "live_request": request,
        }
        validation = validator.execute_fn(case=serialized)
        if validation.status != "succeeded" or not bool(validation.actual.get("valid")):
            raise AssertionError(
                f"candidate DeerFlow Mock failed hard-boundary validation for "
                f"{demand_space_id}: {validation.actual}"
            )
        samples.append(
            {
                "demand_space_id": demand_space_id,
                "scenario": scenario,
                "user_intent": user_intent,
                "query": query,
                "user_context": dict(getattr(intent, "user_context", {}) or {}),
                "request": request,
                "hard_boundary_validation": validation.actual,
            }
        )

    return {
        "status": "succeeded",
        "project_id": spec.project_id,
        "role": "mock",
        "observed_asset_ids": [
            "mock_investigation",
            "mock_investigation_context_builder",
            "mock_business_input_validator",
            "candidate_role",
        ],
        "context_unit_ids": [record.id for record in contract_records],
        "covered_demand_space_ids": sorted(
            item["demand_space_id"] for item in samples
        ),
        "samples": samples,
        "checks": {
            "candidate_instantiated": True,
            "context_builder_loaded_contract": True,
            "candidate_consumed_contract": True,
            "all_demand_spaces_generated": True,
            "hard_boundary_validator_passed": True,
            "no_forbidden_user_language": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run()
    output = Path(args.output)
    write_solidify_probe_result(output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
