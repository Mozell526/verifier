#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

from impl.core.project_loader import load_adapter, load_project, load_project_role_instance, resolve_role_assets
from impl.core.solidify import require_solidify_receipt
from impl.core.portable_artifact import resolve_logical_refs_in_payload, write_portable_export
from impl.core.schema.draft_state import DRAFT_RUN_REPORT_VERSION
from impl.core.schema import normalize_judge_result, normalize_run_trace, to_dict

from fingerprints import current_fingerprint, draft_fingerprint, runner_fingerprint
from load_mock_source import load_mock_source


ProgressCallback = Callable[[Dict[str, Any]], None]
CurrentCompletedCallback = Callable[[Dict[str, Any]], None]


class UnrecoverableProviderFailure(RuntimeError):
    """Provider/account failure that cannot become healthy through retry backoff."""



def validate_iteration_cases(
    role: str,
    cases: Iterable[Dict[str, Any]],
    *,
    path_resolver: Any = None,
) -> list[Dict[str, Any]]:
    """Normalize the whole frozen set before any expensive Role execution."""
    normalized = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise TypeError(f"Draft iteration case[{index}] must be an object")
        try:
            normalized.append(_normalize_case(role, case, path_resolver=path_resolver))
        except Exception as exc:
            raise type(exc)(f"invalid Draft iteration case[{index}]: {exc}") from exc
    return normalized


def run_frozen_iteration(
    project_id: str,
    role: str,
    cases: Iterable[Dict[str, Any]],
    *,
    preflight_query: str = "",
    progress_callback: Optional[ProgressCallback] = None,
    workers: int = 1,
    resume_from: Optional[Path] = None,
    health_check: bool = True,
    retries: int = 0,
) -> Dict[str, Any]:
    """Run one frozen Current/Draft comparison with optional parallel workers.

    ``workers > 1`` executes independent cases concurrently. Each worker thread
    owns isolated Role instances so per-instance runtime state (Attribute
    environment snapshots) is never shared. Completed rows are flushed through
    ``progress_callback`` as they finish, so a caller can persist a partial file
    and resume later with ``resume_from``. Resume only reuses rows whose frozen
    cases hash matches the current call (same start frozen on both sides).
    """
    frozen_cases = [dict(item) for item in cases]
    cases_hash = _stable_hash(frozen_cases)
    base_spec = load_project(project_id)
    current_fp = current_fingerprint(base_spec)
    draft_fp = draft_fingerprint(base_spec, role)
    runner_fp = runner_fingerprint(base_spec)
    normalized_cases = validate_iteration_cases(
        role,
        frozen_cases,
        path_resolver=base_spec.path_resolver,
    )
    current_spec = _spec_for_side(base_spec, role, enabled=False)
    draft_spec = _spec_for_side(base_spec, role, enabled=True)
    solidify_receipt = (
        require_solidify_receipt(
            draft_spec,
            role,
            business_source_staleness_policy="warn",
        )
        if role in {"judge", "mock"}
        else None
    )

    if health_check:
        _probe_llm_endpoint(role)

    resumed = _load_resume_rows(
        resume_from,
        cases_hash,
        {
            "current_fingerprint": current_fp,
            "draft_fingerprint": draft_fp,
            "runner_fingerprint": runner_fp,
        },
    )
    rows: Dict[str, Dict[str, Any]] = dict(resumed)

    attempts = max(1, retries + 1)
    runner = _CaseRunner(role, current_spec, draft_spec)
    run_started = time.monotonic()

    if preflight_query.strip():
        _preflight_role(role, runner.instance("current"), normalized_cases, preflight_query, side="current")
        _preflight_role(role, runner.instance("draft"), normalized_cases, preflight_query, side="draft")

    pending = [
        (index, raw_case, case)
        for index, (raw_case, case) in enumerate(zip(frozen_cases, normalized_cases))
        if _case_key(raw_case, index) not in rows
    ]
    if pending:
        abort_event = threading.Event()
        if workers > 1:
            _run_parallel(
                pending, role, runner, attempts, rows, progress_callback, workers, abort_event
            )
        else:
            _run_serial(pending, role, runner, attempts, rows, progress_callback)
    if _stable_hash(frozen_cases) != cases_hash:
        raise RuntimeError("Draft iteration mutated frozen cases")
    ordered = [rows[key] for key in sorted(rows, key=str)]
    return {
        "schema_version": DRAFT_RUN_REPORT_VERSION,
        "project_id": project_id,
        "role": role,
        "workers": workers,
        "elapsed_seconds": round(time.monotonic() - run_started, 3),
        "case_count": len(ordered),
        "frozen_cases_sha256": cases_hash,
        "current_fingerprint": current_fp,
        "draft_fingerprint": draft_fp,
        "runner_fingerprint": runner_fp,
        "current": {
            "draft_enabled": False,
            "assets": _asset_snapshot(current_spec, role, use_candidate=False),
        },
        "draft": {
            "draft_enabled": True,
            "assets": _asset_snapshot(draft_spec, role, use_candidate=True),
            "solidify_receipt": (
                {
                    "schema_version": solidify_receipt.get("schema_version"),
                    "manifest_sha256": solidify_receipt.get("manifest_sha256"),
                    "role_contract_sha256": solidify_receipt.get("role_contract_sha256"),
                    "runtime_staleness": solidify_receipt.get("runtime_staleness"),
                }
                if solidify_receipt is not None
                else None
            ),
        },
        "rows": ordered,
        "decision": None,
        "note": (
            "Protocol facts only. Draft Skill must decide improvement against frozen Current, "
            "objective, config.review and real experiments; equality or missing evidence is not success."
        ),
    }


def _case_key(raw_case: Mapping[str, Any], index: int) -> Any:
    return raw_case.get("case_key") or raw_case.get("id") or index


def _load_resume_rows(
    resume_from: Optional[Path],
    cases_hash: str,
    expected_fingerprints: Mapping[str, str],
) -> Dict[str, Dict[str, Any]]:
    if resume_from is None or not resume_from.is_file():
        return {}
    try:
        partial = json.loads(resume_from.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"resume partial is not readable JSON: {resume_from}: {exc}") from exc
    if partial.get("frozen_cases_sha256") != cases_hash:
        raise RuntimeError(
            "resume partial was started from a different frozen case set; "
            "delete the partial and restart"
        )
    for name, expected in expected_fingerprints.items():
        if partial.get(name) != expected:
            raise RuntimeError(
                f"resume partial was started from a different {name}; "
                "the run code or assets changed since it was written, so its "
                "rows are stale; delete the partial and restart"
            )
    rows = partial.get("rows")
    if not isinstance(rows, list):
        rows = partial.get("completed_rows")
    resumed: Dict[str, Dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        key = row.get("case_key")
        if key is None:
            continue
        row = dict(row)
        if row.get("current") is None or row.get("draft") is None:
            continue
        if row.get("current_runtime") is None or row.get("draft_runtime") is None:
            continue
        # Rows with side errors or LLM failures are not proven and must be retried.
        failed = (
            row.get("current_error")
            or row.get("draft_error")
            or "LLM 调用失败" in (row.get("current") or {}).get("reasoning_summary", "")
            or "LLM 调用失败" in (row.get("draft") or {}).get("reasoning_summary", "")
        )
        if failed:
            continue
        resumed[str(key)] = row
    return resumed


def _run_serial(
    pending: list[Tuple[int, Mapping[str, Any], Mapping[str, Any]]],
    role: str,
    runner: "_CaseRunner",
    attempts: int,
    rows: Dict[str, Dict[str, Any]],
    progress_callback: Optional[ProgressCallback],
    abort_event: Optional[threading.Event] = None,
) -> None:
    abort_event = abort_event or threading.Event()
    for index, raw_case, case in pending:
        if abort_event.is_set():
            raise UnrecoverableProviderFailure("Draft iteration aborted after provider failure")
        key = _case_key(raw_case, index)
        def current_completed(partial_row: Dict[str, Any]) -> None:
            if progress_callback is not None:
                progress_callback({
                    "phase": "current_completed",
                    "case_index": index,
                    "completed_rows": list(rows.values()),
                    "partial_row": partial_row,
                })

        partial_row, row = _run_one_case(
            role, runner, attempts, index, raw_case, case, abort_event,
            current_completed=current_completed,
        )
        rows[key] = row
        if progress_callback is not None:
            progress_callback({
                "phase": "case_completed",
                "case_index": index,
                "completed_rows": list(rows.values()),
            })
        _assert_formal_runtime_valid(role, "draft", key, row["draft_runtime"])


def _run_parallel(
    pending: list[Tuple[int, Mapping[str, Any], Mapping[str, Any]]],
    role: str,
    runner: "_CaseRunner",
    attempts: int,
    rows: Dict[str, Dict[str, Any]],
    progress_callback: Optional[ProgressCallback],
    workers: int,
    abort_event: Optional[threading.Event] = None,
) -> None:
    lock = threading.Lock()
    abort_event = abort_event or threading.Event()
    def process(item: Tuple[int, Mapping[str, Any], Mapping[str, Any]]) -> Dict[str, Any]:
        if abort_event.is_set():
            raise UnrecoverableProviderFailure("Draft iteration aborted after provider failure")
        index, raw_case, case = item
        key = _case_key(raw_case, index)
        def current_completed(partial_row: Dict[str, Any]) -> None:
            with lock:
                if progress_callback is not None:
                    progress_callback({
                        "phase": "current_completed",
                        "case_index": index,
                        "completed_rows": list(rows.values()),
                        "partial_row": partial_row,
                    })

        _, row = _run_one_case(
            role, runner, attempts, index, raw_case, case, abort_event,
            current_completed=current_completed,
        )
        with lock:
            rows[key] = row
            snapshot = list(rows.values())
            if progress_callback is not None:
                progress_callback({
                    "phase": "case_completed",
                    "case_index": index,
                    "completed_rows": snapshot,
                })
        _assert_formal_runtime_valid(role, "draft", key, row["draft_runtime"])
        return row

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(process, item): item for item in pending}
        try:
            for future in as_completed(futures):
                future.result()
        except UnrecoverableProviderFailure:
            abort_event.set()
            for pending_future in futures:
                pending_future.cancel()
            raise


def _run_one_case(
    role: str,
    runner: "_CaseRunner",
    attempts: int,
    index: int,
    raw_case: Mapping[str, Any],
    case: Mapping[str, Any],
    abort_event: Optional[threading.Event] = None,
    current_completed: Optional[CurrentCompletedCallback] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    key = _case_key(raw_case, index)
    current = _run_side_with_retry(
        role, runner, attempts, "current", case, abort_event
    )
    _assert_formal_runtime_valid(role, "current", key, current["runtime"])
    partial_row = {
        "case_key": key,
        "current": current["payload"],
        "current_runtime": current["runtime"],
        "current_metrics": {"elapsed_seconds": round(current["elapsed"], 6)},
    }
    if current["error"] is not None:
        partial_row["current_error"] = current["error"]
    if current_completed is not None:
        current_completed(dict(partial_row))
    draft = _run_side_with_retry(
        role, runner, attempts, "draft", case, abort_event
    )
    row = {
        **partial_row,
        "draft": draft["payload"],
        "draft_runtime": draft["runtime"],
        "draft_metrics": {"elapsed_seconds": round(draft["elapsed"], 6)},
    }
    if draft["error"] is not None:
        row["draft_error"] = draft["error"]
    return partial_row, row


def _run_side_with_retry(
    role: str,
    runner: "_CaseRunner",
    attempts: int,
    side: str,
    case: Mapping[str, Any],
    abort_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    last: Optional[Dict[str, Any]] = None
    for _attempt in range(attempts):
        if abort_event is not None and abort_event.is_set():
            raise UnrecoverableProviderFailure("Draft iteration aborted after provider failure")
        last = _run_side_once(role, runner, side, case)
        failed = (
            last["error"] is not None
            or "LLM 调用失败" in str(last["payload"].get("reasoning_summary") or "")
            or _side_authority_endpoint_failure(last)
        )
        if not failed:
            return last
        fatal_reason = _unrecoverable_provider_failure(last)
        if fatal_reason is not None:
            if abort_event is not None:
                abort_event.set()
            raise UnrecoverableProviderFailure(
                f"Draft iteration provider failure is not retryable: {fatal_reason}"
            )
        if _is_endpoint_failure(last):
            return last
    return last


_AUTHORITY_ENDPOINT_MARKERS = (
    "rate limit",
    "429",
    "timeout",
    "timed out",
    "unreachable",
    "connection",
    "server error",
    "internal server error",
    "502",
    "503",
    "unknown model",
    "modelprovider",
    "rpm ",
    "token plan",
    "llm 调用失败",
    "llm 请求失败",
    "llm_request_failed",
    "openai",
)


def _side_authority_endpoint_failure(last: Mapping[str, Any]) -> bool:
    """Judge side whose authority.resolve failed on a transient endpoint error.

    authority.md §8.4：执行失败 ≠ 业务 unresolved。authority 工具因限流/连接/
    模型错误失败时，Judge 会诚实落盘 tool_failure 并输出 not_evaluable；但这
    类失败不能当作“真查证后的依据不充分”，本应走退避重试。这里把引用到的
    authority_audit 中的端点类失败升级为 side 级失败，让整侧在退避后重跑，
    而不是把瞬时网关故障直接冻结进比较结果。
    """
    runtime = last.get("runtime") or {}
    audit = runtime.get("authority_audit") or {}
    if not isinstance(audit, Mapping):
        return False
    for entry in audit.values():
        if not isinstance(entry, Mapping) or not entry.get("tool_failure"):
            continue
        text = f"{entry.get('error') or ''}".lower()
        if any(marker in text for marker in _AUTHORITY_ENDPOINT_MARKERS):
            return True
    return False


_UNRECOVERABLE_PROVIDER_MARKERS = (
    "insufficient balance",
    "http 402",
    "status code: 402",
    "invalid api key",
    "incorrect api key",
    "expired api key",
    "authentication failed",
    "unauthorized",
    "quota exhausted",
)


def _provider_failure_text(last: Mapping[str, Any]) -> str:
    payload = last.get("payload") or {}
    parts = [
        str(last.get("error") or ""),
        str(payload.get("error") or ""),
        str(payload.get("reasoning_summary") or ""),
    ]
    runtime = last.get("runtime") or {}
    audit = runtime.get("authority_audit") or {}
    if isinstance(audit, Mapping):
        for entry in audit.values():
            if isinstance(entry, Mapping) and entry.get("tool_failure"):
                parts.append(str(entry.get("error") or ""))
    return " ".join(parts).lower()


def _unrecoverable_provider_failure(last: Mapping[str, Any]) -> Optional[str]:
    """Return a sanitized reason for account/auth failures that retries cannot heal.

    Rate limiting remains transient: generic quota wording is deliberately not
    enough; only exhausted quota/balance or authentication failures abort a run.
    """
    text = _provider_failure_text(last)
    for marker in _UNRECOVERABLE_PROVIDER_MARKERS:
        if marker in text:
            return marker
    return None


def _is_endpoint_failure(last: Mapping[str, Any]) -> bool:
    """Classify a side failure as endpoint/LLM transient vs. business error.

    Only endpoint failures (rate limit, timeout, connection, 5xx, or the
    canonical ``LLM 调用失败`` marker) should drive retry backoff. A business
    or validation error is a real role behavior fact and must not stall the
    batch; it is still retried by the existing loop but without cooling the
    gate.
    """
    if _side_authority_endpoint_failure(last):
        return True
    if "LLM 调用失败" in str(last["payload"].get("reasoning_summary") or ""):
        return True
    if last["error"] is None:
        return False
    text = f"{last['error']} {last['payload'].get('error') or ''}".lower()
    return any(marker in text for marker in _AUTHORITY_ENDPOINT_MARKERS)

def _run_side_once(
    role: str, runner: "_CaseRunner", side: str, case: Mapping[str, Any]
) -> Dict[str, Any]:
    implementation = runner.instance(side)
    started = time.perf_counter()
    error = None
    try:
        output = _run_role(role, implementation, case)
        payload = to_dict(output)
    except Exception as exc:  # noqa: BLE001
        output = None
        payload = _role_error(exc)
        error = payload["error"]
    elapsed = time.perf_counter() - started
    runtime = _runtime_snapshot(role, implementation)
    return {"payload": payload, "error": error, "elapsed": elapsed, "runtime": runtime}


class _CaseRunner:
    """Per-thread isolated Role instances; serial mode reuses one thread."""

    def __init__(self, role: str, current_spec: Any, draft_spec: Any):
        self.role = role
        self.current_spec = current_spec
        self.draft_spec = draft_spec
        self._local = threading.local()

    def instance(self, side: str) -> Any:
        local = self._local
        if not hasattr(local, "current"):
            local.current = _role_instance(
                self.current_spec, self.role, load_adapter(self.current_spec)
            )
            local.draft = _role_instance(
                self.draft_spec, self.role, load_adapter(self.draft_spec)
            )
        return local.current if side == "current" else local.draft


def _probe_llm_endpoint(role: str) -> None:
    """用公共 Router 的缓存健康状态为批跑做快速预检。"""
    if role not in {"judge", "mock"}:
        return
    try:
        from impl.core.llm_client import LlmClient

        client = LlmClient(role=role)
        client._validate_config()
        client.llm_router.refresh_health_if_stale()
        if client.llm_router.active_endpoint_names():
            return
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"LLM endpoint preflight failed: {exc}") from exc
    raise RuntimeError("LLM endpoint preflight failed: all configured endpoints are cooling")


def _spec_for_side(base_spec: Any, role: str, *, enabled: bool) -> Any:
    # ProjectSpec contains immutable MappingProxy-backed environment metadata and
    # a PathResolver. Deep-copying the whole object is unsupported on Python 3.11
    # and is unnecessary: only these mutable configuration trees are changed.
    spec = replace(
        base_spec,
        project=deepcopy(base_spec.project),
        runtime=deepcopy(base_spec.runtime),
        verifier=deepcopy(base_spec.verifier),
        metadata=deepcopy(base_spec.metadata),
    )
    roles = dict(spec.verifier.get("roles") or {})
    role_config = dict(roles.get(role) or {})
    draft = dict(role_config.get("draft") or {})
    draft["enabled"] = enabled
    draft.setdefault("module", f"project://draft/{role}.py")
    role_config["draft"] = draft
    roles[role] = role_config
    spec.verifier["roles"] = roles
    return spec

def _role_error(exc: Exception) -> Dict[str, Any]:
    """Serialize one case-side failure without aborting the frozen comparison."""
    return {
        "status": "error",
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
    }


def _preflight_role(
    role: str,
    implementation: Any,
    cases: list[Dict[str, Any]],
    query: str,
    *,
    side: str,
) -> None:
    """Verify required runtime dependencies without invoking an LLM.

    Attribute evidence registration and Search both depend on the configured
    embedding provider. A formal Current/Draft comparison is invalid when that
    dependency is unavailable, so fail before either side spends model tokens.
    """
    if role != "attribute" or not cases:
        return
    from impl.core.attribute_environment import build_attribute_environment

    environment = build_attribute_environment(implementation.spec, cases[0]["trace"])
    provider = environment.context_runtime.embedding_provider
    vectors = provider.embed([
        f"draft-loop preflight query: {query}",
        "draft-loop preflight material registration",
    ])
    if len(vectors) != 2 or any(
        not vector or any(not math.isfinite(float(value)) for value in vector)
        for vector in vectors
    ):
        raise RuntimeError(f"{side} Attribute embedding preflight returned invalid vectors")


def _role_instance(spec: Any, role: str, adapter: Any) -> Any:
    if role == "mock":
        return adapter.mock()
    instance = load_project_role_instance(spec, role, adapter)
    if instance is None:
        raise RuntimeError(f"project role is unavailable: {spec.project_id}/{role}")
    return instance


def _run_role(role: str, implementation: Any, case: Dict[str, Any]) -> Any:
    if role == "attribute":
        from impl.core.attribute import judge_status

        # Match the production pipeline: a fulfilled Judge result is an
        # immediate not-applicable outcome and must not pay for Context/Tool
        # assembly or external embeddings.  Besides cost, early registration
        # would make a Draft candidate look slower merely because it declares
        # useful investigation assets that this case never needs.
        if judge_status(case["judge_result"]) != "fulfilled":
            from impl.core.attribute_environment import build_attribute_environment

            implementation.configure_execution_environment(
                build_attribute_environment(implementation.spec, case["trace"])
            )
        return implementation.attribute_failure(case["trace"], case["judge_result"])
    if role == "judge":
        return implementation.judge_trace(case["trace"], user_intent=case.get("user_intent"))
    if role == "mock":
        return implementation.generate_mock_case(
            scenario=case.get("scenario"),
            intent=case.get("intent"),
        )
    raise ValueError(f"unsupported Draft role: {role}")


def _runtime_snapshot(role: str, implementation: Any) -> Dict[str, Any]:
    if role == "attribute":
        environment = getattr(implementation, "_attribute_execution_environment", None)
        if environment is None:
            return {"environment": "missing"}
        context = dict(getattr(environment, "last_context", {}) or {})
        run = getattr(environment, "main_context_run", None)
        return {
            "context": run.debug_snapshot() if run is not None else {},
            "tool_calls": list(context.get("_attribute_tool_audit") or []),
            "review_calls": list(context.get("_attribute_review_audit") or []),
            "dynamic_context_units": list(context.get("dynamic_context_units") or []),
            "evidence_registration_errors": list(context.get("evidence_registration_errors") or []),
        }
    if role == "judge":
        # Judge 单次 agentic 会话（authority.md §8）：落盘 authority.resolve
        # Tool audit 与 environment snapshot，供 review 核对 authority 是否
        # 真实调用、是否发生工具失败（能力不可用），与 result.evidence 的
        # authority_runtime 相互印证。
        context = dict(
            getattr(implementation, "_last_judge_context", None)
            or getattr(implementation, "_last_draft_context", None)
            or {}
        )
        authority_tool = context.get("authority_tool")
        audit = dict(getattr(authority_tool, "audit", None) or {})
        return {
            "environment": "ok" if authority_tool is not None else "missing",
            "authority_tool_call_ids": sorted(audit.keys()),
            "authority_audit": {
                str(call_id): to_dict(entry)
                for call_id, entry in audit.items()
            },
            "environment_snapshot_sha256": str(
                context.get("environment_snapshot_sha256") or ""
            ),
            "context_governance": dict(
                context.get("context_governance_report") or {}
            ),
        }
    return {}


def _formal_runtime_failures(role: str, runtime: Mapping[str, Any]) -> list[str]:
    """Return deterministic reasons that make a comparison run invalid.

    This deliberately does not judge attribution quality or ordinary model
    request mistakes. Those remain inputs to the Harness AI review.
    """
    if role == "judge":
        governance = runtime.get("context_governance") or {}
        gate = governance.get("gate") or {}
        if gate.get("mode") == "draft" and gate.get("blocking") is True:
            return ["Draft Context Governance has open blocking findings"]
        return []
    if role != "attribute":
        return []
    failures = []
    if runtime.get("environment") == "missing":
        failures.append("Attribute execution environment is missing")
    context_debug = (runtime.get("context") or {}).get("context_debug") or {}
    for error in context_debug.get("errors") or []:
        if bool(error.get("infrastructure")):
            failures.append(
                f"Context {error.get('operation')}: {error.get('type')}: {error.get('message')}"
            )
    for error in runtime.get("evidence_registration_errors") or []:
        failures.append(f"evidence registration: {error}")
    for call in runtime.get("review_calls") or []:
        error = str(call.get("infrastructure_error") or "").strip()
        if error:
            failures.append(f"review round {call.get('round')}: {error}")
    return failures


def _assert_formal_runtime_valid(
    role: str,
    side: str,
    case_key: Any,
    runtime: Mapping[str, Any],
) -> None:
    failures = _formal_runtime_failures(role, runtime)
    if failures:
        raise RuntimeError(
            f"{side} {role} runtime invalid for case {case_key}: " + "; ".join(failures)
        )


def _normalize_case(
    role: str,
    case: Dict[str, Any],
    *,
    path_resolver: Any = None,
) -> Dict[str, Any]:
    normalized = dict(case)
    if role in {"judge", "attribute"}:
        trace_payload = case.get("trace")
        if path_resolver is not None:
            trace_payload = resolve_logical_refs_in_payload(trace_payload, path_resolver)
        trace = normalize_run_trace(trace_payload)
        if trace is None:
            raise TypeError(f"{role} case requires a valid trace")
        normalized["trace"] = trace
    if role == "attribute":
        judge = normalize_judge_result(case.get("judge_result"))
        if judge is None:
            raise TypeError("attribute case requires a valid judge_result")
        normalized["judge_result"] = judge
    return normalized


def _asset_snapshot(spec: Any, role: str, *, use_candidate: bool) -> list[Dict[str, Any]]:
    return [
        {
            "asset_id": item["mapping"].asset_id,
            "kind": item["mapping"].kind,
            "source": item["source"],
            "location": dict(item["location_ref"].to_mapping()),
            "available": item["available"],
        }
        for item in resolve_role_assets(spec, role, use_candidate=use_candidate)
    ]


def _stable_hash(value: Any) -> str:
    payload = json.dumps(to_dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one frozen Current/Draft protocol iteration.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    parser.add_argument("--cases", required=True, help="JSON/Python case source or Draft mock_source object")
    parser.add_argument("--report", default="")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", type=Path, default=None, help="partial report to resume from")
    parser.add_argument("--health-check", action="store_true", default=True, help="probe LLM endpoint before running")
    parser.add_argument("--no-health-check", dest="health_check", action="store_false")
    parser.add_argument("--retries", type=int, default=3, help="extra attempts per side after the first")
    args = parser.parse_args()

    source: Any = args.cases
    if args.cases.lstrip().startswith(("{", "[")):
        source = json.loads(args.cases)
    loaded = load_mock_source(source)
    result = run_frozen_iteration(
        args.project,
        args.role,
        loaded["iteration_cases"],
        workers=args.workers,
        resume_from=args.resume,
        health_check=args.health_check,
        retries=args.retries,
    )
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        write_portable_export(Path(args.report), result)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
