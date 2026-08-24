"""Machine-computed Draft Loop net score. Harness explains; it does not infer direction.

Comparison key is overall_fulfillment.status only. Same status is a tie. A status
change is a flip. The machine never ranks fulfilled / not_evaluable / not_fulfilled:
direction comes from harness flip_labels citing fulfilled.md. Unlabeled stable
flips cannot count as wins.

A flip enters win/loss only when every replicate of the same revision reproduces
the same (current, draft) status pair. One run is not enough; unstable pairs go
to variance.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

EXCLUDED_REASONS = (
    "human_unresolved",
    "ambiguity_gap",
    "retrieval_gap",
    "tool_interrupt",
    "other",
)
FLIP_DIRECTIONS = ("win", "loss")
_REPLICATE_NAME = re.compile(r"^(?P<stem>.+)-r(?P<n>\d+)\.json$")
_IDENTITY_FIELDS = (
    "frozen_cases_sha256",
    "current_fingerprint",
    "draft_fingerprint",
    "runner_fingerprint",
)


def overall_status(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return ""
    overall = payload.get("overall_fulfillment") or {}
    if isinstance(overall, Mapping):
        return str(overall.get("status") or "").strip().lower()
    return ""


def discover_replicate_paths(primary: Path) -> list[Path]:
    """Return sibling replicate reports ``<stem>-r2.json``, ``<stem>-r3.json``, …"""
    target = Path(primary)
    found: list[tuple[int, Path]] = []
    for path in target.parent.glob(f"{target.stem}-r*.json"):
        match = _REPLICATE_NAME.match(path.name)
        if match is None or match.group("stem") != target.stem:
            continue
        found.append((int(match.group("n")), path))
    return [path for _, path in sorted(found)]


def load_replicate_reports(
    primary: Path,
    primary_report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in discover_replicate_paths(primary):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise TypeError(f"replicate report must be an object: {path}")
        status = raw.get("run_status")
        if status not in {None, "completed"}:
            raise ValueError(f"replicate {path.name} is not a completed run")
        _assert_same_revision(primary_report, raw, path)
        reports.append(dict(raw))
    return reports


def next_replicate_path(primary: Path) -> Path:
    existing = {path.name for path in discover_replicate_paths(primary)}
    index = 2
    while True:
        candidate = Path(primary).with_name(f"{Path(primary).stem}-r{index}.json")
        if candidate.name not in existing and not candidate.exists():
            return candidate
        index += 1


def _assert_same_revision(
    primary: Mapping[str, Any],
    replica: Mapping[str, Any],
    path: Path,
) -> None:
    for field in _IDENTITY_FIELDS:
        expected = primary.get(field)
        actual = replica.get(field)
        if expected and actual and expected != actual:
            raise ValueError(
                f"replicate {path.name} {field} does not match the primary run"
            )


def _normalize_exclusions(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("exclusions must be a list")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"exclusions[{index}] must be an object")
        case_key = str(item.get("case_key") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not case_key:
            raise ValueError(f"exclusions[{index}].case_key is required")
        if reason not in EXCLUDED_REASONS:
            raise ValueError(
                f"exclusions[{index}].reason must be one of {EXCLUDED_REASONS}"
            )
        if reason == "other" and not str(item.get("detail") or "").strip():
            raise ValueError("exclusions reason=other requires detail")
        if case_key in seen:
            raise ValueError(f"duplicate exclusion case_key: {case_key}")
        seen.add(case_key)
        entry = {"case_key": case_key, "reason": reason}
        detail = str(item.get("detail") or "").strip()
        if detail:
            entry["detail"] = detail
        normalized.append(entry)
    return normalized


def _normalize_flip_labels(value: Any) -> dict[str, dict[str, str]]:
    if value is None:
        return {}
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("flip_labels must be a list")
    labels: dict[str, dict[str, str]] = {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"flip_labels[{index}] must be an object")
        case_key = str(item.get("case_key") or "").strip()
        direction = str(item.get("direction") or "").strip()
        clause = str(item.get("clause") or "").strip()
        if not case_key:
            raise ValueError(f"flip_labels[{index}].case_key is required")
        if direction not in FLIP_DIRECTIONS:
            raise ValueError(
                f"flip_labels[{index}].direction must be one of {FLIP_DIRECTIONS}"
            )
        if not clause:
            raise ValueError(
                f"flip_labels[{index}].clause is required (fulfilled.md anchor)"
            )
        if case_key in labels:
            raise ValueError(f"duplicate flip_labels case_key: {case_key}")
        labels[case_key] = {
            "case_key": case_key,
            "direction": direction,
            "clause": clause,
        }
    return labels


def _rows_by_key(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for row in report.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        case_key = str(row.get("case_key") or "")
        if case_key:
            rows[case_key] = row
    return rows


def _status_pair(row: Mapping[str, Any] | None) -> tuple[str, str] | None:
    if row is None:
        return None
    current = overall_status(row.get("current"))
    draft = overall_status(row.get("draft"))
    if not current or not draft:
        return None
    return current, draft


def score_iteration(
    report: Mapping[str, Any],
    exclusions: Any = None,
    *,
    invalid_case_keys: Sequence[str] | None = None,
    flip_labels: Any = None,
    replicates: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    declared = _normalize_exclusions(exclusions)
    declared_keys = {item["case_key"] for item in declared}
    invalid = {str(item) for item in (invalid_case_keys or [])}
    auto: list[dict[str, str]] = []
    for case_key in sorted(invalid - declared_keys):
        auto.append({
            "case_key": case_key,
            "reason": "tool_interrupt",
            "detail": "run_report_invalid_sides",
        })
    excluded = {item["case_key"]: item for item in [*declared, *auto]}
    labels = _normalize_flip_labels(flip_labels)
    replica_reports = [item for item in (replicates or []) if isinstance(item, Mapping)]
    all_reports = [report, *replica_reports]
    stability_ready = len(all_reports) >= 2
    keyed_reports = [_rows_by_key(item) for item in all_reports]

    wins: list[str] = []
    losses: list[str] = []
    ties: list[str] = []
    unlabeled: list[str] = []
    variance: list[str] = []
    observed_flips: list[str] = []
    skipped: list[dict[str, str]] = []
    labeled_keys: set[str] = set()

    for row in report.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        case_key = str(row.get("case_key") or "")
        if not case_key:
            continue
        if case_key in excluded:
            skipped.append(excluded[case_key])
            if case_key in labels:
                raise ValueError(f"flip_labels cannot cover excluded case: {case_key}")
            continue
        primary_pair = _status_pair(row)
        if primary_pair and primary_pair[0] != primary_pair[1]:
            observed_flips.append(case_key)
        pairs = [_status_pair(keyed.get(case_key)) for keyed in keyed_reports]
        if not stability_ready:
            if primary_pair is None or primary_pair[0] == primary_pair[1]:
                ties.append(case_key)
            else:
                variance.append(case_key)
            continue
        if any(item is None for item in pairs) or any(item != pairs[0] for item in pairs):
            variance.append(case_key)
            continue
        current, draft = pairs[0]  # type: ignore[misc]
        if current == draft:
            if case_key in labels:
                raise ValueError(f"flip_labels cannot cover a status tie: {case_key}")
            ties.append(case_key)
            continue
        label = labels.get(case_key)
        if label is None:
            unlabeled.append(case_key)
            continue
        labeled_keys.add(case_key)
        if label["direction"] == "win":
            wins.append(case_key)
        else:
            losses.append(case_key)

    unused = sorted(set(labels) - labeled_keys - set(excluded) - set(variance))
    if unused:
        raise ValueError(
            "flip_labels must cover a stable status flip: " + ", ".join(unused)
        )

    net = len(wins) - len(losses)
    relative_fail = bool(losses or unlabeled)
    return {
        "schema_version": 2,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "unlabeled_flips": unlabeled,
        "variance": variance,
        "observed_flips": observed_flips,
        "excluded": skipped,
        "win_count": len(wins),
        "loss_count": len(losses),
        "tie_count": len(ties),
        "unlabeled_count": len(unlabeled),
        "variance_count": len(variance),
        "excluded_count": len(skipped),
        "net": net,
        "replicate_count": len(all_reports),
        "stability_ready": stability_ready,
        "relative_status": "fail" if relative_fail else "pass",
        "allows_improved": bool(
            net > 0 and not losses and not unlabeled and stability_ready
        ),
    }
