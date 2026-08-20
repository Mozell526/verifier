from __future__ import annotations

from typing import Any, Dict, Optional

from impl.core.judge_protocol import ProjectJudge
from impl.core.schema import JudgeResult, RunTrace, normalize_judge_result, to_dict
from impl.projects.llm_probe.capability import resolve_capability


def _request_payload(trace: RunTrace) -> Dict[str, Any]:
    request = trace.normalized_request if isinstance(trace.normalized_request, dict) else {}
    return dict(request)


def _capability(trace: RunTrace) -> str:
    try:
        return resolve_capability(_request_payload(trace))
    except ValueError as exc:
        return str(exc)


class LlmProbeJudge(ProjectJudge):
    def build_context(self, trace: RunTrace) -> dict:
        request = _request_payload(trace)
        capability = _capability(trace)
        show_schema = request.get("show_schema")
        output = trace.extracted_output if isinstance(trace.extracted_output, dict) else {}
        system_extras = [
            "## 能力描述\n"
            "只根据能力描述判断 output_text 是否兑现了该能力。没有 gold output，不要编造参考答案。\n"
        ]
        if show_schema not in (None, "", {}, []):
            system_extras.append(
                "## show_schema\n"
                "下面指出输出里哪些部分重要。没提到的部分不要当成失败依据。\n"
            )
        return {
            "user_intent": capability,
            "intent_frame": {
                "project_id": self.spec.project_id,
                "downstream_consumer": request.get("capability_ref") or "probed HTTP service",
                "output_semantics": "output_text should fulfill the capability description",
                "capability": capability,
                "show_schema": show_schema,
                "critical_intent_dimensions": ["capability_fulfillment", "show_schema_focus"],
            },
            "system_prompt_extras": system_extras,
            "user_prompt_extras": to_dict({
                "capability": capability,
                "show_schema": show_schema,
                "request": {
                    "url": request.get("url") or "",
                    "method": request.get("method"),
                    "headers": request.get("headers") or {},
                    "body": request.get("body") or {},
                    "capability_ref": request.get("capability_ref") or "",
                },
                "output_text": output.get("output_text") or "",
                "application_boundary": {
                    "scope": "non_streaming_http_llm_probe",
                    "streaming": False,
                },
            }),
        }

    def build_intent_frame(self, trace: RunTrace, context: Optional[dict] = None) -> dict:
        built = context if context is not None else self.build_context(trace)
        frame = dict(built.get("intent_frame") or {})
        frame.setdefault("request_candidates", [
            {"source": "normalized_request.body", "value": (_request_payload(trace).get("body") or {})},
        ])
        return frame

    def normalize_result(self, trace: RunTrace, result: JudgeResult) -> JudgeResult:
        judge_result = normalize_judge_result(result) or result
        actual = trace.extracted_output if isinstance(trace.extracted_output, dict) else {}
        judge_result.actual = actual if actual else (judge_result.actual or {"output_text": ""})
        if judge_result.expected is None:
            judge_result.expected = {}
        return judge_result
