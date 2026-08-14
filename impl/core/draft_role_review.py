"""Role-specific Harness review receipts for Judge/Mock Draft iterations.

The receipt records a human/AI judgment over the frozen Current/Draft report. It
never computes a winner from generic fields and does not modify public Draft Loop
or Role result schemas.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .path_contract import LogicalPathRef, PathScope, logical_ref_for_path
from .portable_artifact import write_active_artifact
from .project_loader import resolve_project_package_root, resolve_role_assets
from .solidify import require_solidify_receipt, solidify_receipt_path


DRAFT_ROLE_REVIEW_VERSION = 1
_ALLOWED_STATUSES = {"pass", "fail", "not_evaluable"}


_TERMINAL_ROLE_FAILURE_EVIDENCE = frozenset({
    "llm_call_failed",
    "llm_output_validation_failed",
})
_DECISION_ROUTES = {
    "improved": {"promotion_checks"},
    "unchanged": {"investigate", "solidify"},
    "regressed": {"investigate", "solidify"},
    "insufficient_evidence": {"investigate", "solidify"},
    "blocked": {"blocked"},
}

JUDGE_REVIEW_CRITERIA = (
    "expectation_support",
    "atomic_pre_actual_expectations",
    "expectation_topology",
    "pre_actual_blocking",
    "dimension_coverage",
    "fulfilled_external_evidence",
    "not_fulfilled_live_boundary",
    "not_evaluable_evidence_gap",
    "missing_output_no_escape",
    "external_constraint_non_attribution",
    "authority_anchor_scope",
    "authority_obligation_consumption",
    "authority_unresolved_conservatism",
    "no_runtime_authority_investigation",
    "no_internal_or_unseen_leakage",
    "relative_improvement_no_regression",
)

MOCK_REVIEW_CRITERIA = (
    "demand_space_coverage",
    "dimension_evaluability",
    "concrete_internal_consistency",
    "variation",
    "no_case_or_judge_hardcode",
    "candidate_consumes_investigation_assets",
    "relative_improvement_no_regression",
)


def role_review_required(spec: Any, role: str) -> bool:
    normalized_role = _role(role)
    selected = resolve_role_assets(spec, normalized_role, use_candidate=True)
    return any(item["mapping"].kind == "investigation" for item in selected)


def draft_role_review_path(
    spec: Any,
    role: str,
    iteration: int,
    *,
    must_exist: bool = True,
) -> Path:
    normalized_role = _role(role)
    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
        raise ValueError("Draft role review iteration must be a positive integer")
    accessor = getattr(spec, "draft_role_review_path", None)
    if callable(accessor):
        return accessor(normalized_role, iteration, must_exist=must_exist)
    path = (
        resolve_project_package_root(spec, must_exist=True)
        / "draft"
        / ".state"
        / normalized_role
        / "iterations"
        / f"{iteration:03d}-role-review.json"
    )
    if must_exist and not path.is_file():
        raise FileNotFoundError(f"Draft role review not found: {path}")
    return path


def write_draft_role_review(
    spec: Any,
    role: str,
    iteration: int,
    *,
    run_report: Path,
    decision: str,
    route: str,
    summary: str,
    criteria: Sequence[Mapping[str, Any]],
    contract_coverage: Sequence[Mapping[str, Any]],
) -> Path:
    normalized_role = _role(role)
    _validate_decision_route(decision, route)
    report_path = _canonical_run_report(spec, normalized_role, iteration, run_report)
    report = _read_object(report_path, "Draft run report")
    solidify = require_solidify_receipt(
        spec,
        normalized_role,
        business_source_staleness_policy=(
            "strict" if route == "promotion_checks" else "warn"
        ),
    )
    if solidify is None:
        raise ValueError(
            "Draft role review receipt is only required for a configured Investigation asset"
        )
    case_keys = _report_case_keys(report)
    normalized_criteria = _validate_criteria(
        normalized_role, criteria,
        report_name=report_path.name, case_keys=case_keys,
    )
    normalized_coverage = _validate_contract_coverage(
        contract_coverage,
        required_source_ids=set(solidify.get("required_source_ids") or []),
        report_name=report_path.name,
        case_keys=case_keys,
    )
    if decision == "improved":
        require_improved_run_report(report)
        _require_improved_relative_criterion(normalized_criteria)
    payload = {
        "schema_version": DRAFT_ROLE_REVIEW_VERSION,
        "project_id": spec.project_id,
        "role": normalized_role,
        "iteration": iteration,
        "run_report": logical_ref_for_path(
            report_path,
            scope=PathScope.PROJECT_PACKAGE,
            roots=spec.path_roots,
            field_path="draft_role_review.run_report",
            sha256=_file_sha256(report_path),
        ),
        "run_report_sha256": _file_sha256(report_path),
        "solidify_receipt_sha256": _file_sha256(
            solidify_receipt_path(spec, normalized_role)
        ),
        "decision": decision,
        "route": route,
        "summary": _text(summary, "Draft role review summary"),
        "contract_coverage": normalized_coverage,
        "criteria": normalized_criteria,
    }
    path = draft_role_review_path(
        spec, normalized_role, iteration, must_exist=False
    )
    return write_active_artifact(
        "draft_role_review",
        path,
        payload,
        repository_root=spec.verifier_root_path(),
    )


def require_draft_role_review(
    spec: Any,
    role: str,
    iteration: int,
    *,
    run_report: Path,
    decision: str | None = None,
    route: str | None = None,
    check_current_solidify: bool = True,
) -> Mapping[str, Any] | None:
    normalized_role = _role(role)
    if not role_review_required(spec, normalized_role):
        return None
    report_path = _canonical_run_report(spec, normalized_role, iteration, run_report)
    path = draft_role_review_path(spec, normalized_role, iteration)
    raw = _read_object(path, "Draft role review")
    allowed = {
        "schema_version",
        "project_id",
        "role",
        "iteration",
        "run_report",
        "run_report_sha256",
        "solidify_receipt_sha256",
        "decision",
        "route",
        "summary",
        "contract_coverage",
        "criteria",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Draft role review contains unknown field: {unknown[0]}")
    # Historical reviews are immutable snapshots of their own run report and
    # stored Solidify hash. A newer candidate may legitimately make the
    # current Solidify receipt stale, so only the active/latest review is
    # coupled to the current receipt and its current source set. Regular Draft
    # review follows candidate-runtime warning semantics; promotion checks are
    # deliberately strict.
    effective_route = str(route or raw.get("route") or "")
    solidify = (
        require_solidify_receipt(
            spec,
            normalized_role,
            business_source_staleness_policy=(
                "strict" if effective_route == "promotion_checks" else "warn"
            ),
        )
        if check_current_solidify
        else None
    )
    if check_current_solidify and solidify is None:
        raise ValueError("configured Investigation asset has no Solidify receipt")
    schema_version = raw.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != DRAFT_ROLE_REVIEW_VERSION
    ):
        raise ValueError(f"unsupported Draft role review version: {path}")
    if (
        raw.get("project_id") != spec.project_id
        or raw.get("role") != normalized_role
        or raw.get("iteration") != iteration
    ):
        raise ValueError(f"Draft role review identity mismatch: {path}")
    raw_report = raw.get("run_report")
    if not isinstance(raw_report, Mapping):
        raise TypeError("Draft role review run_report must be a LogicalPathRef")
    report_ref = LogicalPathRef.from_mapping(
        raw_report, field_path="draft_role_review.run_report"
    )
    expected_report = report_path.relative_to(
        resolve_project_package_root(spec, must_exist=True)
    ).as_posix()
    if (
        report_ref.location_scope is not PathScope.PROJECT_PACKAGE
        or report_ref.location != expected_report
    ):
        raise ValueError("Draft role review is stale: run_report changed")
    if not report_ref.sha256:
        raise ValueError("Draft role review run_report requires sha256")
    actual_report_sha256 = _file_sha256(report_path)
    if report_ref.sha256 != actual_report_sha256:
        raise ValueError("Draft role review is stale: run report hash changed")
    if raw.get("run_report_sha256") != actual_report_sha256:
        raise ValueError("Draft role review is stale: run report hash changed")
    if check_current_solidify and raw.get("solidify_receipt_sha256") != _file_sha256(
        solidify_receipt_path(spec, normalized_role)
    ):
        raise ValueError("Draft role review is stale: Solidify receipt changed")
    _validate_decision_route(str(raw.get("decision") or ""), str(raw.get("route") or ""))
    if decision is not None and raw.get("decision") != decision:
        raise ValueError("Draft role review decision does not match Draft Loop review")
    if route is not None and raw.get("route") != route:
        raise ValueError("Draft role review route does not match Draft Loop review")
    _text(raw.get("summary"), "Draft role review summary")
    case_keys = _report_case_keys(_read_object(report_path, "Draft run report"))
    normalized_criteria = _validate_criteria(
        normalized_role, raw.get("criteria"),
        report_name=report_path.name, case_keys=case_keys,
    )
    _validate_contract_coverage(
        raw.get("contract_coverage"),
        required_source_ids=(
            set(solidify.get("required_source_ids") or [])
            if check_current_solidify and solidify is not None
            else None
        ),
        report_name=report_path.name,
        case_keys=case_keys,
    )
    if raw.get("decision") == "improved":
        require_improved_run_report(_read_object(report_path, "Draft run report"))
        _require_improved_relative_criterion(normalized_criteria)
    return raw


def run_report_invalid_sides(report: Mapping[str, Any]) -> list[str]:
    """Return Current/Draft sides whose execution cannot support improvement.

    This is a deterministic gate, not a quality judgment. It covers both
    infrastructure metadata and terminal Role outputs so a 403, invalid LLM
    output, empty-query exception, or missing execution environment cannot be
    re-labelled as a relative improvement by a review receipt.
    """
    invalid: list[str] = []
    # judge current 侧是生产部署：本身没有 authority runtime，
    # environment=missing 是正常状态而非执行失败（authority.md §8）。
    # Authority 关闭时 draft 同样没有 authority_tool，environment=missing
    # 与 current 一致，不能把整侧判成执行失败。draft missing 而 current ok
    # 才是未接线。
    role = str(report.get("role") or "").strip().lower()
    for row in report.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        case_key = str(row.get("case_key") or "<unknown-case>")
        for side in ("current", "draft"):
            runtime = row.get(f"{side}_runtime") or {}
            if not isinstance(runtime, Mapping):
                runtime = {}
            context = runtime.get("context") or {}
            if not isinstance(context, Mapping):
                context = {}
            context_debug = context.get("context_debug") or {}
            if not isinstance(context_debug, Mapping):
                context_debug = {}
            context_failed = any(
                isinstance(item, Mapping) and bool(item.get("infrastructure"))
                for item in context_debug.get("errors") or []
            )
            review_failed = any(
                isinstance(item, Mapping)
                and str(item.get("infrastructure_error") or "").strip()
                for item in runtime.get("review_calls") or []
            )
            result = row.get(side) or {}
            if not isinstance(result, Mapping):
                result = {}
            evidence = {
                str(item)
                for item in result.get("evidence") or []
                if isinstance(item, str)
            }
            # Judge：authority.resolve 工具失败（能力不可用，如限流）且被某
            # assessment 实际引用时，该 side 的判定依赖不可用能力，不能作为
            # 相对改善的证据（authority.md §8.4：执行失败 ≠ 业务 unresolved）。
            failed_authority_calls = {
                str(call_id)
                for call_id, entry in (runtime.get("authority_audit") or {}).items()
                if isinstance(entry, Mapping) and bool(entry.get("tool_failure"))
            }
            referenced_calls = {
                str(call_id)
                for assessment in (result.get("fulfillment_assessments") or [])
                if isinstance(assessment, Mapping)
                for call_id in (assessment.get("authority_tool_call_ids") or [])
            }
            authority_dependency_failed = bool(
                failed_authority_calls & referenced_calls
            )
            result_failed = (
                str(result.get("status") or "").strip().lower()
                in {"error", "failed", "blocked"}
                or bool(result.get("error"))
                or bool(row.get(f"{side}_error"))
                or bool(evidence & _TERMINAL_ROLE_FAILURE_EVIDENCE)
            )
            environment_missing = runtime.get("environment") == "missing"
            if environment_missing and role == "judge":
                if side == "current":
                    environment_missing = False
                elif side == "draft":
                    current_runtime = row.get("current_runtime") or {}
                    if (
                        isinstance(current_runtime, Mapping)
                        and current_runtime.get("environment") == "missing"
                    ):
                        environment_missing = False
            if (
                environment_missing
                or context_failed
                or bool(runtime.get("evidence_registration_errors"))
                or review_failed
                or authority_dependency_failed
                or result_failed
            ):
                invalid.append(f"{case_key}/{side}")
    return invalid


def require_improved_run_report(report: Mapping[str, Any]) -> None:
    """Deterministic floor for recording improved: the run must be comparable.

    A single aborted Draft row does not veto the round. improved is blocked
    only when every Draft side is invalid, so a one-row all-fail report still
    fails and a mixed 1/N abort does not.
    """
    if report.get("run_status") != "completed" or not report.get("rows"):
        raise ValueError("improved review requires a completed non-empty Current/Draft report")
    rows = [row for row in report.get("rows") or [] if isinstance(row, Mapping)]
    draft_invalid = [
        side for side in run_report_invalid_sides(report) if side.endswith("/draft")
    ]
    if len(draft_invalid) >= len(rows):
        raise ValueError(
            "improved review cannot use a run with no comparable Draft sides: "
            + ", ".join(draft_invalid)
        )


def _require_improved_relative_criterion(criteria: Sequence[Mapping[str, Any]]) -> None:
    relative = next(
        (
            item for item in criteria
            if item.get("criterion_id") == "relative_improvement_no_regression"
        ),
        None,
    )
    if relative is None or relative.get("status") != "pass":
        raise ValueError(
            "improved role review requires relative_improvement_no_regression to pass"
        )


def _report_case_keys(report: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("case_key"))
        for row in report.get("rows") or []
        if isinstance(row, Mapping) and row.get("case_key") is not None
    }


def _validate_report_anchors(
    evidence: Sequence[str], owner: str, report_name: str, case_keys: set[str]
) -> None:
    """Reject `<report>#<case>` anchors that do not resolve to a real case.

    Free-text evidence stays untouched; only the exact anchor convention used
    by review receipts is dereferenced, so a pass finding cannot cite a
    fabricated case.
    """
    prefix = f"{report_name}#"
    for item in evidence:
        if not item.startswith(prefix):
            continue
        fragment = item[len(prefix):]
        if fragment.startswith("rows[") or fragment in case_keys:
            continue
        raise ValueError(
            f"{owner} evidence references a case absent from the run report: {item}"
        )


def _validate_criteria(
    role: str,
    value: Any,
    *,
    report_name: str,
    case_keys: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Draft role review criteria must be a list")
    expected = set(_criteria_ids(role))
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"Draft role review criteria[{index}] must be an object")
        allowed = {"criterion_id", "status", "evidence", "finding"}
        unknown = sorted(set(item) - allowed)
        if unknown:
            raise ValueError(
                f"Draft role review criteria[{index}] contains unknown field: {unknown[0]}"
            )
        criterion_id = _text(
            item.get("criterion_id"), f"criteria[{index}].criterion_id"
        )
        if criterion_id in seen:
            raise ValueError(f"duplicate Draft role review criterion: {criterion_id}")
        seen.add(criterion_id)
        if criterion_id not in expected:
            raise ValueError(f"unknown {role} Draft review criterion: {criterion_id}")
        status = _text(item.get("status"), f"criteria[{index}].status")
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"unsupported Draft role review status: {status}")
        evidence = _string_list(item.get("evidence"), f"criteria[{index}].evidence")
        _validate_report_anchors(
            evidence, f"criteria[{index}]", report_name, case_keys
        )
        finding = _text(item.get("finding"), f"criteria[{index}].finding")
        normalized.append(
            {
                "criterion_id": criterion_id,
                "status": status,
                "evidence": evidence,
                "finding": finding,
            }
        )
    missing = sorted(expected - seen)
    if missing:
        raise ValueError(
            f"Draft role review is missing {role} criteria: " + ", ".join(missing)
        )
    return sorted(normalized, key=lambda item: _criteria_ids(role).index(item["criterion_id"]))


def _validate_contract_coverage(
    value: Any,
    *,
    required_source_ids: set[str] | None,
    report_name: str,
    case_keys: set[str],
) -> list[dict[str, Any]]:
    """Validate review evidence against the receipt generation it belongs to.

    Current reviews are checked against the active Solidify receipt. Historical
    reviews keep their own coverage snapshot because a later Solidify cycle may
    legitimately replace the active source set; their run-report integrity is
    still checked separately.
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Draft role review contract_coverage must be a list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"contract_coverage[{index}] must be an object")
        allowed = {"source_id", "evidence"}
        unknown = sorted(set(item) - allowed)
        if unknown:
            raise ValueError(
                f"contract_coverage[{index}] contains unknown field: {unknown[0]}"
            )
        source_id = _text(item.get("source_id"), f"contract_coverage[{index}].source_id")
        if source_id in seen:
            raise ValueError(f"duplicate contract coverage source_id: {source_id}")
        seen.add(source_id)
        if required_source_ids is not None and source_id not in required_source_ids:
            raise ValueError(f"contract coverage references unknown source ID: {source_id}")
        coverage_evidence = _string_list(
            item.get("evidence"), f"contract_coverage[{index}].evidence"
        )
        _validate_report_anchors(
            coverage_evidence, f"contract_coverage[{index}]", report_name, case_keys
        )
        normalized.append(
            {
                "source_id": source_id,
                "evidence": coverage_evidence,
            }
        )
    missing = sorted(required_source_ids - seen) if required_source_ids is not None else []
    if missing:
        raise ValueError(
            "Draft role review does not cover contract source IDs: " + ", ".join(missing)
        )
    return sorted(normalized, key=lambda item: item["source_id"])


def _canonical_run_report(spec: Any, role: str, iteration: int, path: Path) -> Path:
    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
        raise ValueError("Draft role review iteration must be a positive integer")
    project_root = resolve_project_package_root(spec, must_exist=True)
    expected = (
        project_root
        / "draft"
        / ".state"
        / role
        / "iterations"
        / f"{iteration:03d}-run.json"
    ).resolve()
    actual = Path(path).resolve()
    if actual != expected:
        raise ValueError(f"Draft role review run_report must be {expected}")
    if not actual.is_file():
        raise FileNotFoundError(f"Draft role review run report not found: {actual}")
    return actual


def _criteria_ids(role: str) -> tuple[str, ...]:
    return JUDGE_REVIEW_CRITERIA if role == "judge" else MOCK_REVIEW_CRITERIA


def _validate_decision_route(decision: str, route: str) -> None:
    if decision not in _DECISION_ROUTES or route not in _DECISION_ROUTES[decision]:
        raise ValueError(f"invalid Draft role review decision/route: {decision}/{route}")


def _read_object(path: Path, owner: str) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError(f"{owner} must be an object: {path}")
    return raw


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _role(role: str) -> str:
    normalized = str(role or "").strip()
    if normalized not in {"judge", "mock"}:
        raise ValueError(f"Draft role review supports only Judge/Mock: {normalized or '<empty>'}")
    return normalized


def _text(value: Any, owner: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} is required")
    return value.strip()


def _string_list(value: Any, owner: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{owner} must be a list of strings")
    if not value:
        raise ValueError(f"{owner} must be non-empty")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise TypeError(f"{owner}[{index}] must be a non-empty string")
        result.append(item.strip())
    if len(result) != len(set(result)):
        raise ValueError(f"{owner} contains duplicate values")
    return result
