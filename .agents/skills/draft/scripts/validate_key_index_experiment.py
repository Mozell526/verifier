#!/usr/bin/env python3
"""Validate Key-Index investigation, simulation, and frozen-loop selection evidence.

A passing run writes a deterministic gate receipt to
``draft/.state/<role>/key-index-gates/<experiment_id>-<phase>.json``.
``validate_investigation.py`` requires a matching selection receipt for every
Key-Index registered in the Investigation Manifest, so an index cannot be
registered as a formal asset without passing this gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

_CHANNELS = {"exact", "lexical", "embedding", "rerank"}
_CHANNEL_DECISIONS = {"experiment", "deferred", "rejected", "not_applicable"}
_REQUIRED_CATEGORIES = {
    "stable_identifier", "source_term", "source_paraphrase",
    "ambiguity_multi_object", "unsupported", "irrelevant", "search_to_load",
}
# A probe can cover more than one concern. These aliases keep reports concise.
_CATEGORY_ALIASES = {
    "stable_identifier": {"stable_identifier", "source_term"},
    "search_to_load": {"search_to_load", "source_term", "source_paraphrase", "ambiguity_multi_object"},
}
_REQUIRED_METRICS = {
    "top8_recall_rate", "irrelevant_rejection_rate",
    "search_to_load_resolution_rate", "average_loaded_entries", "average_loaded_chars",
}
_REQUIRED_SUITE = {
    "index_key", "collection_ref", "builder", "projection_fields", "search_strategy",
    "target_ref_template", "resolver", "load_operation",
}


def _present(value: object) -> bool:
    return bool(str(value or "").strip())


def _covered(categories: set[str], required: str) -> bool:
    return bool(categories & _CATEGORY_ALIASES.get(required, {required}))


def _validate_investigation(report: dict) -> list[str]:
    errors: list[str] = []
    for key in ("experiment_id", "project_id", "role", "source_revision"):
        if not _present(report.get(key)):
            errors.append(f"{key} is required")
    if report.get("schema_version") != 2:
        errors.append("schema_version must be 2")

    profile = report.get("collection_profile") or {}
    for key in ("collection_ref", "object_count", "stable_identifier", "load_boundary", "runtime_need"):
        if not profile.get(key):
            errors.append(f"collection_profile.{key} is required")
    if "full_load_pressure_observed" not in profile:
        errors.append("collection_profile.full_load_pressure_observed is required")

    consideration = report.get("channel_consideration") or {}
    for channel in sorted(_CHANNELS):
        item = consideration.get(channel) or {}
        decision = item.get("decision")
        if decision not in _CHANNEL_DECISIONS:
            errors.append(f"channel_consideration.{channel}.decision must be one of {sorted(_CHANNEL_DECISIONS)}")
        if not _present(item.get("reason")):
            errors.append(f"channel_consideration.{channel}.reason is required")

    candidates = report.get("candidates") or []
    exclusions = report.get("alternative_exclusions") or []
    if len(candidates) < 2 and not exclusions:
        errors.append("at least baseline plus one alternative is required, or record alternative_exclusions")
    for index, exclusion in enumerate(exclusions):
        if not _present(exclusion.get("alternative")) or not _present(exclusion.get("reason")):
            errors.append(f"alternative_exclusions[{index}] requires alternative and reason")
    return errors


def _passes(metrics: dict, thresholds: dict) -> bool:
    return (
        float(metrics["top8_recall_rate"]) >= float(thresholds["top8_recall_rate_min"])
        and float(metrics["irrelevant_rejection_rate"]) >= float(thresholds["irrelevant_rejection_rate_min"])
        and float(metrics["search_to_load_resolution_rate"]) >= float(thresholds["search_to_load_resolution_rate_min"])
        and float(metrics["average_loaded_entries"]) <= float(thresholds["average_loaded_entries_max"])
    )


def _validate_simulation(report: dict) -> list[str]:
    errors = _validate_investigation(report)
    profile = report.get("collection_profile") or {}
    probe_sets = report.get("probe_sets") or {}
    total_rows: dict[str, int] = {}
    for split in ("development", "holdout"):
        probe_set = probe_sets.get(split) or {}
        if not _present(probe_set.get("sha256")):
            errors.append(f"probe_sets.{split}.sha256 is required")
        count = int(probe_set.get("count") or 0)
        total_rows[split] = count
        if count <= 0:
            errors.append(f"probe_sets.{split}.count must be positive")
    aggregate_categories: set[str] = set()
    for split in ("development", "holdout"):
        aggregate_categories.update((probe_sets.get(split) or {}).get("categories") or [])
    missing = sorted(category for category in _REQUIRED_CATEGORIES if not _covered(aggregate_categories, category))
    if missing:
        errors.append(f"probe_sets aggregate categories missing coverage: {missing}")
    if (probe_sets.get("holdout") or {}).get("used_for_tuning") is not False:
        errors.append("probe_sets.holdout.used_for_tuning must be false")
    if not _present(report.get("builder_output_sha256")):
        errors.append("builder_output_sha256 is required")
    if float(report.get("all_entry_target_resolution_rate") or 0) != 1.0:
        errors.append("all_entry_target_resolution_rate must be 1.0")

    thresholds = report.get("thresholds") or {}
    for key in ("top8_recall_rate_min", "irrelevant_rejection_rate_min", "search_to_load_resolution_rate_min", "average_loaded_entries_max"):
        if key not in thresholds:
            errors.append(f"thresholds.{key} is required")

    candidate_ids: set[str] = set()
    qualified: set[str] = set()
    for candidate in report.get("candidates") or []:
        cid = str(candidate.get("candidate_id") or "")
        if not cid or cid in candidate_ids:
            errors.append(f"candidate_id missing or duplicate: {cid!r}")
            continue
        candidate_ids.add(cid)
        channels = set(candidate.get("retrieval_channels") or [])
        defaults = set(candidate.get("default_retrieval_channels") or [])
        if not channels:
            errors.append(f"{cid}: retrieval_channels must not be empty")
        if not channels <= _CHANNELS:
            errors.append(f"{cid}: unknown retrieval_channels {sorted(channels - _CHANNELS)}")
        if not defaults <= channels:
            errors.append(f"{cid}: default_retrieval_channels must be a subset of retrieval_channels")
        consideration = report.get("channel_consideration") or {}
        for channel in channels:
            if (consideration.get(channel) or {}).get("decision") != "experiment":
                errors.append(f"{cid}: declared channel {channel!r} must have decision=experiment")
        if "embedding" in channels:
            audit = candidate.get("embedding_audit") or {}
            for key in ("model", "model_version", "projection_version"):
                if not _present(audit.get(key)):
                    errors.append(f"{cid}: embedding_audit.{key} is required for embedding channel")
        if candidate.get("source_derived") is not True:
            errors.append(f"{cid}: source_derived must be true")
        if candidate.get("forbidden_inputs"):
            errors.append(f"{cid}: forbidden_inputs must be empty")
        if candidate.get("deterministic_builder") is not True:
            errors.append(f"{cid}: deterministic_builder must be true")
        provenance = candidate.get("projection_provenance") or {}
        if not provenance.get("source_fields"):
            errors.append(f"{cid}: projection_provenance.source_fields is required")
        if provenance.get("ai_authored_terms") is not False:
            errors.append(f"{cid}: projection_provenance.ai_authored_terms must be false")
        suite = candidate.get("suite") or {}
        for key in sorted(_REQUIRED_SUITE):
            if not suite.get(key):
                errors.append(f"{cid}: suite.{key} is required")
        if suite.get("collection_ref") != profile.get("collection_ref"):
            errors.append(f"{cid}: suite.collection_ref mismatch")

        split_passes: list[bool] = []
        for split in ("development", "holdout"):
            result = (candidate.get("results") or {}).get(split) or {}
            if result.get("deterministic_search") is not True:
                errors.append(f"{cid}: results.{split}.deterministic_search must be true")
            metrics = result.get("metrics") or {}
            missing_metrics = sorted(_REQUIRED_METRICS - set(metrics))
            if missing_metrics:
                errors.append(f"{cid}: results.{split} missing metrics {missing_metrics}")
                split_passes.append(False)
            elif all(key in thresholds for key in ("top8_recall_rate_min", "irrelevant_rejection_rate_min", "search_to_load_resolution_rate_min", "average_loaded_entries_max")):
                split_passes.append(_passes(metrics, thresholds))
            rows = result.get("rows") or []
            if len(rows) != total_rows.get(split, 0):
                errors.append(f"{cid}: results.{split}.rows must match probe count")
            for row in rows:
                if not row.get("probe_id") or "query" not in row or "required_targets" not in row:
                    errors.append(f"{cid}: every {split} row needs probe_id/query/required_targets")
                for hit in row.get("hits") or []:
                    matched = set(hit.get("matched_channels") or [])
                    if not matched:
                        errors.append(f"{cid}: every SearchHit must declare matched_channels")
                    if not matched <= channels:
                        errors.append(f"{cid}: SearchHit uses undeclared channels {sorted(matched - channels)}")
                    if not _present(hit.get("key")) or hit.get("resolved") is not True:
                        errors.append(f"{cid}: every SearchHit must resolve to a real target")
        if len(split_passes) == 2 and all(split_passes):
            qualified.add(cid)

    decision = report.get("decision") or {}
    shortlist = set(decision.get("shortlist") or [])
    status = decision.get("status")
    if not shortlist and status not in {"no_index", "unresolved"}:
        errors.append("decision.shortlist must contain a simulation-qualified candidate unless status is no_index/unresolved")
    if status in {"no_index", "unresolved"} and not _present(decision.get("reason")):
        errors.append(f"decision.reason is required when status={status}")
    if not shortlist <= candidate_ids:
        errors.append("decision.shortlist references unknown candidates")
    if not shortlist <= qualified:
        errors.append("decision.shortlist contains candidates that fail development or holdout thresholds")
    if decision.get("status") not in {"provisional", "selected", "no_index", "unresolved"}:
        errors.append("decision.status must be provisional, selected, no_index, or unresolved")
    return errors


def _validate_selection(report: dict) -> list[str]:
    errors = _validate_simulation(report)
    decision = report.get("decision") or {}
    shortlist = set(decision.get("shortlist") or [])
    selected = str(decision.get("selected_candidate") or "")
    if decision.get("status") != "selected":
        errors.append("selection gate requires decision.status=selected")
    if not selected or selected not in shortlist:
        errors.append("selected_candidate must be in shortlist")
    evidence = decision.get("loop_evidence")
    if not isinstance(evidence, dict):
        errors.append("selected candidate requires loop_evidence")
        return errors
    for key in ("loop_id", "iteration", "report_path"):
        if not evidence.get(key):
            errors.append(f"loop_evidence.{key} is required")
    if evidence.get("business_no_regression") is not True:
        errors.append("loop_evidence.business_no_regression must be true")
    if evidence.get("objective_improved") is not True:
        errors.append("loop_evidence.objective_improved must be true")
    if evidence.get("full_collection_fallback_observed") is not False:
        errors.append("loop_evidence.full_collection_fallback_observed must be false")
    for key in ("draft_prompt_tokens", "draft_latency_seconds"):
        if evidence.get(key) is None:
            errors.append(f"loop_evidence.{key} is required")
    audit = evidence.get("search_load_authority_audit") or {}
    if audit.get("passed") is not True:
        errors.append("loop_evidence.search_load_authority_audit.passed must be true")
    return errors


def validate(report: dict, *, phase: str = "simulation", require_selected: bool = False) -> list[str]:
    if require_selected:
        phase = "selection"
    if phase == "investigate":
        return _validate_investigation(report)
    if phase == "simulation":
        return _validate_simulation(report)
    if phase == "selection":
        return _validate_selection(report)
    return [f"unknown phase: {phase}"]


def _covered_index_keys(report: dict, phase: str) -> list[str]:
    """Index keys this receipt vouches for: selection covers the selected
    candidate, simulation covers the shortlist, investigate covers nothing."""
    decision = report.get("decision") or {}
    if phase == "selection":
        chosen = {str(decision.get("selected_candidate") or "")}
    elif phase == "simulation":
        chosen = {str(item) for item in decision.get("shortlist") or []}
    else:
        return []
    keys: set[str] = set()
    for candidate in report.get("candidates") or []:
        if str(candidate.get("candidate_id") or "") not in chosen:
            continue
        key = str(((candidate.get("suite") or {}).get("index_key")) or "").strip()
        if key:
            keys.add(key)
    return sorted(keys)


def write_gate_receipt(report_path: Path, report: dict, phase: str) -> Path:
    from impl.core.portable_artifact import write_portable_export
    from impl.core.project_loader import load_project, resolve_project_package_root

    spec = load_project(str(report["project_id"]))
    package_root = resolve_project_package_root(spec, must_exist=True)
    resolved_report = report_path.resolve()
    try:
        report_location = resolved_report.relative_to(package_root).as_posix()
    except ValueError as exc:
        raise ValueError(
            "Key-Index experiment report must live inside the project package "
            f"so its receipt stays auditable: {resolved_report}"
        ) from exc
    decision = report.get("decision") or {}
    receipt = {
        "schema_version": 1,
        "project_id": str(report["project_id"]),
        "role": str(report["role"]),
        "experiment_id": str(report["experiment_id"]),
        "phase": phase,
        "report_location": report_location,
        "report_sha256": hashlib.sha256(resolved_report.read_bytes()).hexdigest(),
        "decision_status": str(decision.get("status") or ""),
        "selected_candidate": str(decision.get("selected_candidate") or ""),
        "index_keys": _covered_index_keys(report, phase),
    }
    receipt_path = (
        package_root / "draft" / ".state" / str(report["role"]) / "key-index-gates"
        / f"{report['experiment_id']}-{phase}.json"
    )
    write_portable_export(receipt_path, receipt)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--phase", choices=("investigate", "simulation", "selection"), default="simulation")
    parser.add_argument("--require-selected", action="store_true", help="compatibility alias for --phase selection")
    args = parser.parse_args()
    phase = "selection" if args.require_selected else args.phase
    report = json.loads(args.report.read_text())
    errors = validate(report, phase=phase)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    receipt_path = write_gate_receipt(args.report, report, phase)
    print(f"Key-Index {phase} gate passed")
    print(f"Gate receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
