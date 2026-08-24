from __future__ import annotations

from pathlib import Path

import pytest

from impl.core.draft_pending import (
    assert_run_allowed,
    extend_item,
    load_pending,
    overdue_items,
    save_pending,
    upsert_items,
)


def test_overdue_after_three_rounds() -> None:
    items = []
    upsert_items(
        items,
        kind="excluded_case",
        key="083",
        reason="human_unresolved",
        route="human",
        iteration=1,
    )
    assert overdue_items(items, 4) == []
    assert overdue_items(items, 5)
    extend_item(items, "excluded_case:083")
    assert overdue_items(items, 5) == []


def _state_dir(tmp_path: Path) -> Path:
    state = tmp_path / "impl" / "projects" / "demo" / "draft" / ".state" / "judge"
    state.mkdir(parents=True)
    return state


def test_stale_rename_blocks_run(tmp_path: Path) -> None:
    state = _state_dir(tmp_path)
    (state / "investigation-gate-feedback.json.stale-condition_compare-mismatch").write_text(
        "{}", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="stale-renamed"):
        assert_run_allowed(state, 1)


def test_overdue_pending_blocks_run(tmp_path: Path) -> None:
    state = _state_dir(tmp_path)
    save_pending(
        state,
        {
            "schema_version": 1,
            "items": [{
                "id": "excluded_case:083",
                "kind": "excluded_case",
                "key": "083",
                "reason": "human_unresolved",
                "route": "human",
                "first_iteration": 1,
                "extensions": 0,
            }],
        },
        repository_root=tmp_path,
    )
    with pytest.raises(RuntimeError, match="3-round"):
        assert_run_allowed(state, 5)
    assert load_pending(state)["items"]
