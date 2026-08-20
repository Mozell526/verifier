from __future__ import annotations

import json
import urllib.error
from typing import Any, Dict

from impl.core.live_protocol import LiveServiceUnavailableError, RealServiceLive, SingleTurnLive
from impl.core.live_transport import LiveHTTPStatusError, LiveTransport
from impl.core.project_loader import load_project
from impl.core.schema import ExecutionTraceEvent, LiveRequest, ProjectSpec
from impl.projects.llm_probe.capability import resolve_capability

APPLICATION_BOUNDARY = {
    "scope": "non_streaming_http_llm_probe",
    "streaming": False,
}


def _stringify(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def resolve_http(request: Dict[str, Any], spec: ProjectSpec) -> tuple[str, str, Dict[str, str], Dict[str, Any], float]:
    if not isinstance(request, dict):
        raise ValueError("llm_probe request must be an object")
    body = request.get("body")
    if not isinstance(body, dict):
        raise ValueError("llm_probe request.body must be a JSON object")
    url = str(request.get("url") or "").strip()
    raw_method = request.get("method")
    method = str(raw_method).strip().upper() if raw_method else ""
    headers = {
        str(key): str(value)
        for key, value in dict(request.get("headers") or {}).items()
    }
    primary = spec.require_service("primary")
    timeout = float(primary["timeout_seconds"])
    ref = str(request.get("capability_ref") or "").strip()
    if not url:
        if not ref:
            raise ValueError("llm_probe request 需要 url 或 capability_ref")
        service = load_project(ref).require_service("primary")
        url = str(service["base_url"]).rstrip("/") + "/" + str(service["endpoint"]).lstrip("/")
        if not method:
            method = str(service["method"]).upper()
        timeout = float(service["timeout_seconds"])
    if not method:
        method = str(primary["method"]).upper()
    if method not in {"POST", "PUT", "PATCH"}:
        raise ValueError(f"llm_probe 只发非流式 JSON 写方法，收到 {method}")
    resolve_capability(request)
    return url, method, headers, body, timeout


def _reject_streaming(transport: LiveTransport) -> None:
    for exchange in transport.exchanges:
        headers = {
            str(key).lower(): str(value)
            for key, value in dict(exchange.response_headers or {}).items()
        }
        content_type = headers.get("content-type") or ""
        if "text/event-stream" in content_type:
            raise RuntimeError("llm_probe 拒绝流式响应 text/event-stream")


class LlmProbeLive(RealServiceLive, SingleTurnLive):
    """按 case 信封发非流式 HTTP，响应收成字符串。"""

    def deliver_real(self, request: Any, transport: LiveTransport) -> LiveTransport:
        payload = request if isinstance(request, dict) else {}
        url, method, headers, body, timeout = resolve_http(payload, self.spec)
        try:
            transport.request(
                method,
                url,
                json_body=body,
                headers=headers,
                timeout=timeout,
                carries_live_request=True,
                contributes_raw_response=True,
            )
        except LiveHTTPStatusError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LiveServiceUnavailableError(f"llm_probe target unavailable: {exc}") from exc
        _reject_streaming(transport)
        return transport

    def extract_output(self, raw_response: list[Any]) -> Dict[str, Any]:
        payload = raw_response[0] if raw_response else None
        return {"output_text": _stringify(payload)}

    def application_boundary(self, raw_response: Any, extracted_output: Dict[str, Any], request: LiveRequest) -> Dict[str, Any]:
        return dict(APPLICATION_BOUNDARY)

    def project_fields(self, raw_response: Any, extracted_output: Dict[str, Any], request: LiveRequest, application_boundary: Dict[str, Any]) -> Dict[str, Any]:
        payload = request.normalized_request if isinstance(request, LiveRequest) else request
        payload = payload if isinstance(payload, dict) else {}
        return {
            "capability_ref": payload.get("capability_ref") or "",
            "capability": payload.get("capability") or "",
            "show_schema": payload.get("show_schema"),
        }

    def build_execution_trace(self, raw_response: Any, extracted_output: Dict[str, Any], request: LiveRequest) -> list:
        payload = request.normalized_request if isinstance(request, LiveRequest) else request
        payload = payload if isinstance(payload, dict) else {}
        return [
            ExecutionTraceEvent(
                stage="request_normalization",
                status="ok" if isinstance(payload.get("body"), dict) else "failed",
                evidence={"capability_ref": payload.get("capability_ref") or ""},
            ),
            ExecutionTraceEvent(
                stage="http_call",
                status="ok" if raw_response else "failed",
                evidence={"url": payload.get("url") or "", "method": payload.get("method")},
            ),
            ExecutionTraceEvent(
                stage="output_stringify",
                status="ok" if str((extracted_output or {}).get("output_text") or "") else "suspicious",
                evidence={"output_chars": len(str((extracted_output or {}).get("output_text") or ""))},
            ),
        ]
