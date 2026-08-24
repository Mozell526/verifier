"""Hard-boundary validation for DeerFlow Mock Current/Draft review."""
from __future__ import annotations

import re
from typing import Any

from impl.tools import ToolResult, VerifiableTool


_PARAMETERS = {
    "type": "object",
    "properties": {
        "case": {
            "type": "object",
            "description": "Serialized MockBuildResult or generated case containing scenario, user intent and live request input.",
        }
    },
    "required": ["case"],
}
_INTERNAL = re.compile(
    r"verifier|judge|evaluation|mock\s*agent|prompt|system[_ ]?prompt|"
    r"thread_id|trace_id|org_id|user_id|JSON|HTTP|API|端口|"
    r"[/\\][\w.-]+[/\\]|\.(?:py|md|json|yaml)\b|读取.{0,6}文件|修改.{0,6}文件|仓库|源码",
    re.IGNORECASE,
)
_IMPLEMENTATION_IDENTIFIER = re.compile(
    r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}\b",
    re.IGNORECASE,
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _scenario(case: dict[str, Any]) -> str:
    metadata = _mapping(case.get("metadata"))
    return str(case.get("scenario") or metadata.get("scenario") or "").strip()


def _message(case: dict[str, Any]) -> str:
    request = _mapping(case.get("live_request") or case.get("input"))
    request_input = _mapping(request.get("input"))
    messages = request_input.get("messages")
    if not isinstance(messages, list):
        return str(case.get("query") or "").strip()
    for item in reversed(messages):
        if isinstance(item, dict) and str(item.get("role") or "user") == "user":
            return str(item.get("content") or "").strip()
    return ""


def build_mock_business_input_validate_tool() -> VerifiableTool:
    tool_id = "deerflow.mock_business_input_validate"
    description = (
        "Deterministically validate one generated DeerFlow Mock case for request-schema shape "
        "and hard user-knowledge boundaries without enumerating valid intents or preferred wording."
    )
    applicable_scenario = (
        "Use after Current or Draft generates a DeerFlow Mock case and before treating that case "
        "as request-shape and hard-boundary valid; complete semantic "
        "quality remains a Harness review responsibility."
    )

    def execute(**kwargs: Any) -> ToolResult:
        case = kwargs.get("case")
        if not isinstance(case, dict):
            return ToolResult(
                tool_id=tool_id,
                status="inconclusive",
                evidence="validation requires one serialized generated case",
                missing_evidence=["case"],
            )
        scenario = _scenario(case)
        message = _message(case)
        user_intent = str(case.get("user_intent") or "").strip()
        combined = "\n".join(item for item in (message, user_intent) if item)
        failures: list[str] = []
        if not message:
            failures.append("missing_user_message")
        if _INTERNAL.search(combined) or _IMPLEMENTATION_IDENTIFIER.search(combined):
            failures.append("system_internal_language")
        request = _mapping(case.get("live_request") or case.get("input"))
        request_shape_ok = isinstance(request.get("input"), dict) and isinstance(request.get("config"), dict)
        if not request_shape_ok:
            failures.append("invalid_live_request_shape")
        return ToolResult(
            tool_id=tool_id,
            status="succeeded",
            actual={
                "valid": not failures,
                "scenario": scenario,
                "user_message": message,
                "user_intent": user_intent,
                "request_shape_ok": request_shape_ok,
                "failures": failures,
            },
            evidence="applied deterministic request-shape and hard user-knowledge boundary checks",
            boundary_limits=[
                "The validator does not enumerate valid user intents or require domain keywords.",
                "Population breadth, naturalness and constrained-intent fidelity require Harness review.",
                "Assistant correctness and downstream business results require separate Live/Judge evidence.",
            ],
        )

    execute.__name__ = "deerflow_mock_business_input_validate"
    execute.__doc__ = description
    return VerifiableTool(
        tool_id=tool_id,
        description=description,
        applicable_scenario=applicable_scenario,
        parameters=_PARAMETERS,
        execute_fn=execute,
    )
