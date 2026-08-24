#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Mapping, Optional

from impl.core.draft_role_review import (
    draft_role_review_path,
    require_draft_role_review,
    require_improved_run_report,
    role_review_required,
)
from impl.core.investigation import detect_source_revision
from impl.core.path_contract import (
    LogicalPathRef,
    PathResolver,
    PathRoots,
    PathScope,
    logical_ref_for_path,
)
from impl.core.portable_artifact import write_active_artifact, write_portable_export
from impl.core.project_loader import load_project
from impl.core.schema.draft_state import (
    DRAFT_LOOP_STATE_VERSION,
    DRAFT_RUN_REPORT_VERSION,
    DraftEvidencePointer,
    DraftLoopIteration,
    DraftLoopState,
)

from fingerprints import (
    current_fingerprint as compute_current_fingerprint,
    draft_fingerprint as compute_draft_fingerprint,
    runner_fingerprint,
)
from load_mock_source import load_mock_source
from run_iteration import run_frozen_iteration, validate_iteration_cases


LOOP_STATE_VERSION = DRAFT_LOOP_STATE_VERSION
LOOP_ARCHIVE_VERSION = 1
_DECISION_ROUTES = {
    "improved": {"promotion_checks"},
    "unchanged": {"investigate", "solidify"},
    "regressed": {"investigate", "solidify"},
    "insufficient_evidence": {"investigate", "solidify"},
    "blocked": {"blocked"},
}
# Presence of a gate feedback file means the owning gate failed and has not
# been re-run to success; the loop must not consume budget on top of it.
_GATE_FEEDBACK_FILES = (
    "investigation-gate-feedback.json",
    "solidify-gate-feedback.json",
)
# Judge harness analysis must cite a fulfilled.md anchor: a 判断顺序 step,
# a § scenario/clause, a 反面 checklist item, 歧义-缺, 检索缺口, or 不计分.
_JUDGE_HARNESS_ANCHOR = re.compile(r"§|反面|判断顺序|歧义|检索缺口|不计分")


def start_loop(
    project_id: str,
    role: str,
    cases_source: Any,
    *,
    objective: str,
    review: str,
    max_iterations: int,
    restart: bool = False,
) -> DraftLoopState:
    if not objective.strip() or not review.strip():
        raise ValueError("Draft Loop requires non-empty objective and review")
    if max_iterations < 1:
        raise ValueError("Draft Loop max_iterations must be positive")
    spec = load_project(project_id)
    state_path = _state_path(spec, role)
    if state_path.exists() and not restart:
        raise FileExistsError(f"Draft Loop already exists: {state_path}; use --restart")
    cases = list(load_mock_source(cases_source)["iteration_cases"])
    if not cases:
        raise ValueError("Draft Loop requires non-empty iteration cases")
    validate_iteration_cases(role, cases, path_resolver=spec.path_resolver)
    state_dir = state_path.parent
    state_dir.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        previous = _read_state(state_path)
        _assert_identity(previous, project_id, role)
        _archive_loop_revision(spec, state_dir, previous)
        _clear_active_loop_files(state_dir)
    cases_path = state_dir / "iteration-cases.json"
    write_active_artifact(
        "draft_iteration_cases",
        cases_path,
        cases,
        repository_root=spec.verifier_root_path(),
    )
    source_revision = (
        detect_source_revision(spec.source_root_path()) if spec.has_business_source else ""
    )
    state = DraftLoopState(
        schema_version=LOOP_STATE_VERSION,
        project_id=project_id,
        role=role,
        objective=objective.strip(),
        review=review.strip(),
        max_iterations=max_iterations,
        cases_sha256=_stable_hash(cases),
        frozen_current_sha256=compute_current_fingerprint(spec),
        source_revision=source_revision,
    )
    _write_state(spec, state_path, state)
    return state


def _archive_loop_revision(spec: Any, state_dir: Path, state: DraftLoopState) -> Path:
    """Snapshot the complete active role state before a loop restart.

    Historical files remain byte-for-byte copies. ``archive.json`` is the
    portable index that makes the snapshot auditable even though the active
    logical paths in archived receipts are later reused by a new loop.
    """
    history_dir = state_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    revision = _next_archive_revision(history_dir)
    destination = history_dir / f"{revision:03d}"
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{revision:03d}-", dir=str(history_dir))
    )
    try:
        files: list[dict[str, Any]] = []
        for source in _active_revision_files(state_dir):
            relative = source.relative_to(state_dir)
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            files.append(
                {
                    "path": relative.as_posix(),
                    "sha256": _file_sha256(target),
                    "size_bytes": target.stat().st_size,
                }
            )
        if not any(item["path"] == "loop.json" for item in files):
            raise RuntimeError("Draft Loop restart cannot archive a missing loop.json")
        archive = {
            "schema_version": LOOP_ARCHIVE_VERSION,
            "project_id": state.project_id,
            "role": state.role,
            "revision": revision,
            "loop_status": state.status,
            "loop_sha256": _file_sha256(state_dir / "loop.json"),
            "files": files,
        }
        write_portable_export(temporary / "archive.json", archive)
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def _active_revision_files(state_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in state_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(state_dir)
        if relative.parts and relative.parts[0] == "history":
            continue
        files.append(path)
    return sorted(files)


def _next_archive_revision(history_dir: Path) -> int:
    revisions = [
        int(path.name)
        for path in history_dir.iterdir()
        if path.is_dir() and path.name.isdigit()
    ]
    return max(revisions, default=0) + 1


def _clear_active_loop_files(state_dir: Path) -> None:
    for name in ("loop.json", "iteration-cases.json"):
        (state_dir / name).unlink(missing_ok=True)
    iterations_dir = state_dir / "iterations"
    if iterations_dir.exists():
        shutil.rmtree(iterations_dir)


def run_iteration(
    project_id: str, role: str, workers: int = 1, retries: int = 3
) -> Mapping[str, Any]:
    spec = load_project(project_id)
    state_path = _state_path(spec, role)
    state = _read_state(state_path)
    _assert_identity(state, project_id, role)
    if state.status not in {"active"}:
        raise ValueError(f"Draft Loop is not active: status={state.status}")
    pending_feedback = [
        state_path.parent / name
        for name in _GATE_FEEDBACK_FILES
        if (state_path.parent / name).is_file()
    ]
    if pending_feedback:
        raise RuntimeError(
            "unresolved Draft gate feedback blocks this run; follow the "
            "harness_prompt and re-run the owning gate until it passes: "
            + ", ".join(str(path) for path in pending_feedback)
        )
    from impl.core.draft_pending import assert_run_allowed
    from impl.core.draft_score import next_replicate_path
    from impl.core.solidify import require_solidify_receipt

    current_fingerprint = compute_current_fingerprint(spec)
    draft_fingerprint = compute_draft_fingerprint(spec, role)
    replicate = False
    if state.iterations and not state.iterations[-1].decision:
        if state.iterations[-1].draft_fingerprint != draft_fingerprint:
            raise ValueError("previous Draft iteration still awaits Harness review")
        replicate = True
    pending_iteration = len(state.iterations) if replicate else len(state.iterations) + 1
    assert_run_allowed(state_path.parent, pending_iteration)
    try:
        require_solidify_receipt(spec, role)
    except ValueError as exc:
        if "stale" in str(exc):
            raise ValueError(
                f"{exc}. 候选已在 solidify 之外变更，先重跑 scripts/solidify.py 更新收据"
            ) from exc
        raise
    if not replicate and len(state.iterations) >= state.max_iterations:
        state.status = "blocked"
        _write_state(spec, state_path, state)
        raise RuntimeError("Draft Loop reached max_iterations without proven improvement")
    source_drift = _assert_frozen_current(spec, state)
    cases = json.loads((state_path.parent / "iteration-cases.json").read_text(encoding="utf-8"))
    if _stable_hash(cases) != state.cases_sha256:
        raise RuntimeError("Draft Loop iteration cases changed after freezing")

    iteration_number = len(state.iterations) if replicate else len(state.iterations) + 1
    primary_path = state_path.parent / "iterations" / f"{iteration_number:03d}-run.json"
    primary_path.parent.mkdir(parents=True, exist_ok=True)
    if replicate:
        report_path = next_replicate_path(primary_path)
    else:
        report_path = primary_path
        # A restarted loop begins iteration numbering from one. Remove artifacts
        # with the same number before running so callers cannot mistake a
        # previous loop's completed report for the active iteration.
        report_path.unlink(missing_ok=True)
        for leftover in primary_path.parent.glob(f"{primary_path.stem}-r*.json"):
            leftover.unlink()
    partial_path = report_path.with_name(report_path.stem + ".partial.json")
    resume_from = _resume_candidate(spec, state, partial_path)
    if resume_from is None:
        partial_path.unlink(missing_ok=True)

    report = _execute_frozen_run(
        spec,
        state,
        project_id=project_id,
        role=role,
        cases=cases,
        report_path=report_path,
        partial_path=partial_path,
        current_fingerprint=current_fingerprint,
        draft_fingerprint=draft_fingerprint,
        source_drift=source_drift,
        workers=workers,
        retries=retries,
        resume_from=resume_from,
    )
    if not replicate:
        state.iterations.append(DraftLoopIteration(
            iteration=iteration_number,
            run_report=_project_ref(spec, report_path, "draft_loop.run_report"),
            draft_fingerprint=draft_fingerprint,
        ))
        _write_state(spec, state_path, state)
    return report


def _execute_frozen_run(
    spec: Any,
    state: DraftLoopState,
    *,
    project_id: str,
    role: str,
    cases: Any,
    report_path: Path,
    partial_path: Path,
    current_fingerprint: str,
    draft_fingerprint: str,
    source_drift: Mapping[str, Any],
    workers: int,
    retries: int,
    resume_from: Optional[Path],
) -> dict[str, Any]:
    in_progress_rows: dict[str, dict[str, Any]] = {}

    def persist_progress(event: Mapping[str, Any]) -> None:
        event_data = dict(event)
        phase = event_data.get("phase")
        partial_row = event_data.get("partial_row")
        if phase == "current_completed" and isinstance(partial_row, Mapping):
            key = partial_row.get("case_key")
            if key is not None:
                in_progress_rows[str(key)] = dict(partial_row)
        elif phase == "case_completed":
            completed_keys = {
                str(row.get("case_key"))
                for row in event_data.get("completed_rows") or []
                if isinstance(row, Mapping) and row.get("case_key") is not None
            }
            for key in completed_keys:
                in_progress_rows.pop(key, None)
        event_data["in_progress_rows"] = list(in_progress_rows.values())
        write_portable_export(partial_path, {
            "schema_version": DRAFT_RUN_REPORT_VERSION,
            "run_status": "running",
            "project_id": project_id,
            "role": role,
            "frozen_cases_sha256": state.cases_sha256,
            "current_fingerprint": current_fingerprint,
            "draft_fingerprint": draft_fingerprint,
            "runner_fingerprint": runner_fingerprint(spec),
            **event_data,
        })

    try:
        report = run_frozen_iteration(
            project_id,
            role,
            cases,
            preflight_query=state.objective,
            progress_callback=persist_progress,
            workers=workers,
            resume_from=resume_from,
            retries=retries,
        )
        report["schema_version"] = DRAFT_RUN_REPORT_VERSION
        if report.get("run_status") != "error":
            report["run_status"] = "completed"
        report["source_revision_drift"] = source_drift
        report["frozen_cases_sha256"] = state.cases_sha256
        report["current_fingerprint"] = current_fingerprint
        report["draft_fingerprint"] = draft_fingerprint
        report["runner_fingerprint"] = runner_fingerprint(spec)
        write_portable_export(report_path, report)
    except Exception as exc:
        partial = {}
        if partial_path.is_file():
            partial = json.loads(partial_path.read_text(encoding="utf-8"))
        failed_report = {
            **partial,
            "schema_version": DRAFT_RUN_REPORT_VERSION,
            "run_status": "failed",
            "project_id": project_id,
            "role": role,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
        write_portable_export(report_path, failed_report)
        if not state.iterations or state.iterations[-1].decision:
            state.iterations.append(DraftLoopIteration(
                iteration=len(state.iterations) + 1,
                run_report=_project_ref(spec, report_path, "draft_loop.run_report"),
                draft_fingerprint=draft_fingerprint,
            ))
            _write_state(spec, _state_path(spec, role), state)
        partial_path.unlink(missing_ok=True)
        raise RuntimeError(f"Draft iteration failed; partial facts preserved at {report_path}: {exc}") from exc

    partial_path.unlink(missing_ok=True)
    return report



def _resume_candidate(
    spec: Any, state: DraftLoopState, partial_path: Path
) -> Optional[Path]:
    """Return the partial report as a resume source only when it was started
    from the exact same frozen start (same iteration cases and same Current,
    Draft and Runner fingerprints). Anything else is stale and must be
    discarded."""
    if not partial_path.is_file():
        return None
    try:
        partial = json.loads(partial_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(partial, Mapping):
        return None
    if partial.get("frozen_cases_sha256") != state.cases_sha256:
        return None
    if partial.get("current_fingerprint") != compute_current_fingerprint(spec):
        return None
    if partial.get("draft_fingerprint") != compute_draft_fingerprint(spec, state.role):
        return None
    if partial.get("runner_fingerprint") != runner_fingerprint(spec):
        return None
    rows = partial.get("rows")
    if not isinstance(rows, list):
        rows = partial.get("completed_rows")
    if not isinstance(rows, list) or not rows:
        return None
    return partial_path


def record_review(
    project_id: str,
    role: str,
    *,
    decision: str,
    route: str,
    reason: str,
    evidence: list[str],
) -> DraftLoopState:
    spec = load_project(project_id)
    state_path = _state_path(spec, role)
    state = _read_state(state_path)
    _assert_identity(state, project_id, role)
    if not state.iterations or state.iterations[-1].decision:
        raise ValueError("Draft Loop has no unreviewed iteration")
    if decision not in _DECISION_ROUTES or route not in _DECISION_ROUTES[decision]:
        raise ValueError(f"invalid Draft Loop decision/route: {decision}/{route}")
    if not reason.strip() or not evidence:
        raise ValueError("Draft Loop review requires a reason and evidence pointers")
    latest = state.iterations[-1]
    report_path = _resolve_reference(spec, latest.run_report, "draft_loop.run_report")
    if role in {"judge", "mock"} and role_review_required(spec, role):
        review_path = draft_role_review_path(spec, role, latest.iteration)
        require_draft_role_review(
            spec,
            role,
            latest.iteration,
            run_report=report_path,
            decision=decision,
            route=route,
        )
        if not _evidence_mentions_path(state_path, evidence, review_path):
            raise ValueError(
                "Judge/Mock Draft Loop review must cite the validated role review artifact"
            )
        # A blocked review records an infrastructure failure; there are no
        # comparable per-case results to tabulate.
        if decision != "blocked":
            table_path = _require_comparison_table(role, report_path)
            if not _evidence_mentions_path(state_path, evidence, table_path):
                raise ValueError(
                    "Judge/Mock Draft Loop review must cite the per-case comparison table"
                )
    evidence = _validate_review_evidence(spec, state_path, latest, evidence)
    if decision == "improved":
        report_path = _resolve_reference(spec, latest.run_report, "draft_loop.run_report")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        require_improved_run_report(report)
    latest.decision = decision
    latest.route = route
    latest.reason = reason.strip()
    latest.evidence = evidence
    if route == "promotion_checks":
        state.status = "ready_for_promotion_checks"
    elif route == "blocked":
        state.status = "blocked"
    else:
        state.status = "active"
    _write_state(spec, state_path, state)
    return state


def _require_comparison_table(role: str, report_path: Path) -> Path:
    """Deterministic per-case comparison-table gate for Judge/Mock reviews.

    The renderer emits facts and `-` placeholders; the Harness must fill the
    final analysis column for every frozen case before the review is accepted.
    Judge analyses must additionally cite a fulfilled.md anchor so the review
    yardstick stays on the spec instead of drifting to live/production output.
    """
    table_path = report_path.with_name(report_path.stem + "-comparison-table.md")
    if not table_path.is_file():
        raise ValueError(
            f"Draft Loop review requires the rendered comparison table: {table_path}"
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_cases = {
        str(row.get("case_key"))
        for row in report.get("rows") or []
        if isinstance(row, Mapping) and row.get("case_key") is not None
    }
    rows = _parse_comparison_rows(table_path)
    table_cases = {case for case, _ in rows}
    if expected_cases and table_cases != expected_cases:
        missing = sorted(expected_cases - table_cases)
        extra = sorted(table_cases - expected_cases)
        raise ValueError(
            "comparison table does not match the frozen run report cases: "
            f"missing={missing} extra={extra}"
        )
    unfilled = sorted(case for case, analysis in rows if analysis in {"", "-"})
    if unfilled:
        raise ValueError(
            "comparison table harness analysis is not filled for: "
            + ", ".join(unfilled)
        )
    if role == "judge":
        unanchored = sorted(
            case for case, analysis in rows
            if not _JUDGE_HARNESS_ANCHOR.search(analysis)
        )
        if unanchored:
            raise ValueError(
                "judge comparison-table harness analysis must cite fulfilled.md "
                "anchors (判断顺序 step, § clause, 反面 item, 歧义-缺, 检索缺口, or 不计分) for: "
                + ", ".join(unanchored)
            )
    return table_path


def _parse_comparison_rows(table_path: Path) -> list[tuple[str, str]]:
    """Return (case_key, harness_analysis) pairs from the rendered table."""
    rows: list[tuple[str, str]] = []
    header_seen = False
    for line in table_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not header_seen:
            header_seen = True
            continue
        if cells and all(cell and set(cell) <= {"-", ":", " "} for cell in cells):
            continue  # markdown separator row
        if len(cells) < 2:
            continue
        rows.append((cells[0], cells[-1]))
    return rows


def _state_path(spec: Any, role: str) -> Path:
    return spec.project_package_path(
        f"draft/.state/{role}/loop.json",
        field_path=f"draft.{role}.loop_state",
        must_exist=False,
    )


def _read_state(path: Path) -> DraftLoopState:
    if not path.is_file():
        raise FileNotFoundError(f"Draft Loop state not found: {path}")
    return DraftLoopState.from_mapping(json.loads(path.read_text(encoding="utf-8")))


def _write_state(spec: Any, path: Path, state: DraftLoopState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_active_artifact(
        "draft_loop",
        path,
        state.to_mapping(),
        repository_root=spec.verifier_root_path(),
    )


def _evidence_mentions_path(
    state_path: Path, evidence: list[str], expected: Path
) -> bool:
    expected_resolved = expected.resolve()
    for pointer in evidence:
        raw_path = str(pointer).partition("#")[0].strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = state_path.parent / path
        if path.resolve() == expected_resolved:
            return True
    return False


def _validate_review_evidence(
    spec: Any,
    state_path: Path,
    latest: DraftLoopIteration,
    evidence: list[str],
) -> list[DraftEvidencePointer]:
    normalized = [str(item).strip() for item in evidence if str(item).strip()]
    if not normalized:
        raise ValueError("Draft Loop review evidence pointers are empty")
    resolved_paths: set[Path] = set()
    portable: list[DraftEvidencePointer] = []
    for pointer in normalized:
        raw_path, separator, fragment = pointer.partition("#")
        path = Path(raw_path)
        if not path.is_absolute():
            path = state_path.parent / path
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"Draft Loop review evidence does not exist: {pointer}")
        resolved_paths.add(path)
        portable.append(DraftEvidencePointer(
            artifact=_portable_evidence_ref(spec, path),
            pointer=f"#{fragment}" if separator else "",
        ))
    report_path = _resolve_reference(spec, latest.run_report, "draft_loop.run_report")
    if report_path.resolve() not in resolved_paths:
        raise ValueError("Draft Loop review must cite the latest Current/Draft run report")
    return portable


def _project_roots(spec: Any) -> PathRoots:
    configured = getattr(spec, "path_roots", None)
    if configured is None:
        raise RuntimeError(f"project {spec.project_id} has no PathRoots")
    return configured


def _project_ref(spec: Any, path: Path, field_path: str) -> LogicalPathRef:
    return logical_ref_for_path(
        path.resolve(),
        scope=PathScope.PROJECT_PACKAGE,
        roots=_project_roots(spec),
        field_path=field_path,
        sha256=_file_sha256(path),
    )


def _portable_evidence_ref(spec: Any, path: Path) -> LogicalPathRef:
    roots = _project_roots(spec)
    resolved = path.resolve()
    candidates = (
        (PathScope.PROJECT_PACKAGE, roots.project_package),
        (PathScope.VERIFIER_REPO, roots.verifier_repo),
        (PathScope.BUSINESS_SOURCE, roots.business_source),
    )
    for scope, root in candidates:
        if root is not None and resolved.is_relative_to(Path(root).resolve()):
            return logical_ref_for_path(
                resolved,
                scope=scope,
                roots=roots,
                field_path="draft_loop.evidence",
                sha256=_file_sha256(resolved),
            )
    raise ValueError(f"Draft Loop review evidence is outside registered roots: {path}")


def _resolve_reference(spec: Any, reference: LogicalPathRef, field_path: str) -> Path:
    if not reference.sha256:
        raise ValueError(f"{field_path} requires sha256 before active use")
    path = reference.resolve(
        PathResolver(_project_roots(spec)),
        field_path=field_path,
        expected_type="file",
    ).physical
    actual = _file_sha256(path)
    if actual != reference.sha256:
        raise ValueError(
            f"{field_path} content hash changed: expected={reference.sha256}, actual={actual}"
        )
    return path


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _assert_identity(state: DraftLoopState, project_id: str, role: str) -> None:
    if state.project_id != project_id or state.role != role:
        raise ValueError("Draft Loop state identity mismatch")


def _assert_frozen_current(spec: Any, state: DraftLoopState) -> dict:
    """Assert frozen Current is unchanged; return business source drift info (non-blocking)."""
    current = compute_current_fingerprint(spec)
    if current != state.frozen_current_sha256:
        raise RuntimeError("frozen Current changed; start a new Draft Loop revision")
    current_source = (
        detect_source_revision(spec.source_root_path()) if spec.has_business_source else ""
    )
    drifted = bool(current_source and current_source != state.source_revision)
    return {
        "business_source_revision_drifted": drifted,
        "frozen_source_revision": state.source_revision,
        "current_source_revision": current_source,
    }


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist and enforce one Draft current/draft loop.")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--project", required=True)
    start.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    start.add_argument("--cases", required=True)
    start.add_argument("--objective", required=True)
    start.add_argument("--review", required=True)
    start.add_argument("--max-iterations", type=int, default=5)
    start.add_argument("--restart", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--project", required=True)
    run.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    run.add_argument(
        "--workers",
        type=int,
        default=0,
        help="parallel case workers (0 = execution.batch_concurrency_default)",
    )
    run.add_argument(
        "--retries",
        type=int,
        default=3,
        help="extra attempts per side after the first (default 3)",
    )
    review = sub.add_parser("review")
    review.add_argument("--project", required=True)
    review.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    review.add_argument("--decision", required=True, choices=tuple(_DECISION_ROUTES))
    review.add_argument("--route", required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--evidence", required=True, help="JSON list of report pointers")
    status = sub.add_parser("status")
    status.add_argument("--project", required=True)
    status.add_argument("--role", required=True, choices=("attribute", "judge", "mock"))
    args = parser.parse_args()

    if args.command == "start":
        source: Any = args.cases
        if args.cases.lstrip().startswith(("{", "[")):
            source = json.loads(args.cases)
        result: Any = start_loop(
            args.project,
            args.role,
            source,
            objective=args.objective,
            review=args.review,
            max_iterations=args.max_iterations,
            restart=args.restart,
        )
    elif args.command == "run":
        workers = args.workers
        if workers <= 0:
            from impl.core.config import resolve_batch_concurrency
            workers = resolve_batch_concurrency()
        result = run_iteration(args.project, args.role, workers=workers, retries=args.retries)
    elif args.command == "review":
        evidence = json.loads(args.evidence)
        if not isinstance(evidence, list):
            raise TypeError("--evidence must be a JSON list")
        result = record_review(
            args.project,
            args.role,
            decision=args.decision,
            route=args.route,
            reason=args.reason,
            evidence=evidence,
        )
    else:
        spec = load_project(args.project)
        result = _read_state(_state_path(spec, args.role))
    serializable = result.to_mapping() if isinstance(result, DraftLoopState) else result
    print(json.dumps(serializable, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
