from __future__ import annotations

import json
from pathlib import Path

import pytest

from impl.core.draft_score import (
    discover_replicate_paths,
    next_replicate_path,
    score_iteration,
)


def _row(key: str, current: str, draft: str) -> dict:
    return {
        "case_key": key,
        "current": {"overall_fulfillment": {"status": current}},
        "draft": {"overall_fulfillment": {"status": draft}},
    }


def _label(key: str, direction: str, clause: str = "fulfilled.md 反面 1") -> dict:
    return {"case_key": key, "direction": direction, "clause": clause}


def test_single_run_flips_are_variance_not_wins() -> None:
    report = {
        "rows": [
            _row("w1", "not_fulfilled", "fulfilled"),
            _row("l1", "fulfilled", "not_fulfilled"),
            _row("t1", "fulfilled", "fulfilled"),
        ]
    }
    score = score_iteration(report)
    assert score["wins"] == []
    assert score["losses"] == []
    assert score["ties"] == ["t1"]
    assert score["variance"] == ["w1", "l1"]
    assert score["observed_flips"] == ["w1", "l1"]
    assert score["stability_ready"] is False
    assert score["allows_improved"] is False
    assert score["relative_status"] == "pass"


def test_status_rank_is_not_inferred() -> None:
    report = {"rows": [_row("n1", "not_evaluable", "not_fulfilled")]}
    replica = {"rows": [_row("n1", "not_evaluable", "not_fulfilled")]}
    unlabeled = score_iteration(report, replicates=[replica])
    assert unlabeled["unlabeled_flips"] == ["n1"]
    assert unlabeled["wins"] == []
    assert unlabeled["losses"] == []
    assert unlabeled["allows_improved"] is False
    assert unlabeled["relative_status"] == "fail"

    labeled = score_iteration(
        report,
        flip_labels=[_label("n1", "win", "fulfilled.md 反面 9")],
        replicates=[replica],
    )
    assert labeled["wins"] == ["n1"]
    assert labeled["net"] == 1
    assert labeled["allows_improved"] is True


def test_labeled_stable_win_and_loss() -> None:
    report = {
        "rows": [
            _row("w1", "not_fulfilled", "fulfilled"),
            _row("l1", "fulfilled", "not_fulfilled"),
            _row("t1", "fulfilled", "fulfilled"),
        ]
    }
    replica = {
        "rows": [
            _row("w1", "not_fulfilled", "fulfilled"),
            _row("l1", "fulfilled", "not_fulfilled"),
            _row("t1", "fulfilled", "fulfilled"),
        ]
    }
    score = score_iteration(
        report,
        flip_labels=[_label("w1", "win"), _label("l1", "loss")],
        replicates=[replica],
    )
    assert score["wins"] == ["w1"]
    assert score["losses"] == ["l1"]
    assert score["ties"] == ["t1"]
    assert score["net"] == 0
    assert score["stability_ready"] is True
    assert score["relative_status"] == "fail"
    assert score["allows_improved"] is False


def test_exclusions_remove_cases_from_tally() -> None:
    report = {"rows": [_row("w1", "not_fulfilled", "fulfilled"), _row("x1", "fulfilled", "not_fulfilled")]}
    replica = {"rows": [_row("w1", "not_fulfilled", "fulfilled"), _row("x1", "fulfilled", "not_fulfilled")]}
    score = score_iteration(
        report,
        [{"case_key": "x1", "reason": "ambiguity_gap"}],
        flip_labels=[_label("w1", "win")],
        replicates=[replica],
    )
    assert score["wins"] == ["w1"]
    assert score["losses"] == []
    assert score["net"] == 1
    assert score["allows_improved"] is True


def test_unstable_flip_is_variance() -> None:
    report = {"rows": [_row("v1", "fulfilled", "not_fulfilled")]}
    replica = {"rows": [_row("v1", "not_fulfilled", "not_fulfilled")]}
    score = score_iteration(
        report,
        flip_labels=[_label("v1", "win")],
        replicates=[replica],
    )
    assert score["variance"] == ["v1"]
    assert score["wins"] == []
    assert score["allows_improved"] is False


def test_invalid_sides_auto_excluded() -> None:
    report = {"rows": [_row("w1", "not_fulfilled", "fulfilled")]}
    score = score_iteration(report, invalid_case_keys=["w1"])
    assert score["wins"] == []
    assert score["excluded_count"] == 1
    assert score["allows_improved"] is False


def test_label_on_tie_is_rejected() -> None:
    report = {"rows": [_row("t1", "fulfilled", "fulfilled")]}
    replica = {"rows": [_row("t1", "fulfilled", "fulfilled")]}
    with pytest.raises(ValueError, match="status tie"):
        score_iteration(
            report,
            flip_labels=[_label("t1", "win")],
            replicates=[replica],
        )


def test_replicate_path_helpers(tmp_path: Path) -> None:
    primary = tmp_path / "001-run.json"
    primary.write_text("{}", encoding="utf-8")
    assert next_replicate_path(primary).name == "001-run-r2.json"
    r2 = tmp_path / "001-run-r2.json"
    r2.write_text("{}", encoding="utf-8")
    (tmp_path / "001-run-r2.partial.json").write_text("{}", encoding="utf-8")
    assert [path.name for path in discover_replicate_paths(primary)] == ["001-run-r2.json"]
    assert next_replicate_path(primary).name == "001-run-r3.json"
