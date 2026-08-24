import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from impl.projects.client_search.draft.probes.judge_authority_matrix_probe import (
    build_report,
)


PROBES = Path("impl/projects/client_search/draft/probes")
SEED_STATUSES = ("fulfilled", "not_fulfilled", "not_evaluable")
RESOLUTION_STATUSES = (
    "supported",
    "contradicted",
    "unresolved",
    "ungoverned",
    "gap_only",
)


def _combination_key(row):
    config = row["config"]
    return (
        config["authority_enabled"],
        config["authority_required"],
        config["authority_availability"],
        config["compact_material_backed"],
        config["mock_resolution_status"],
        config["judge_seed_status"],
    )


def _expected_combination_keys():
    expected = set()
    for authority_required in (False, True):
        for seed_status in SEED_STATUSES:
            expected.add((
                False,
                authority_required,
                "disabled",
                None,
                None,
                seed_status,
            ))
    for seed_status in SEED_STATUSES:
        expected.add((True, False, "available", None, None, seed_status))
        for resolution_status in RESOLUTION_STATUSES:
            expected.add((
                True,
                True,
                "available",
                False,
                resolution_status,
                seed_status,
            ))
        expected.add((True, True, "unavailable", True, None, seed_status))
        expected.add((True, True, "unavailable", False, None, seed_status))
    return expected


def test_authority_quadrant_suite_uses_frozen_real_cases_without_answer_injection():
    suite = json.loads((PROBES / "judge-authority-quadrants.json").read_text())
    frozen_path = PROBES / suite["frozen_source"]
    frozen_bytes = frozen_path.read_bytes()
    frozen = json.loads(frozen_bytes)
    frozen_ids = {str(item.get("case_id") or item.get("id")) for item in frozen}

    assert len(suite["normal_case_ids"]) >= suite["minimum_distinct_normal_cases"]
    assert len(suite["authority_case_ids"]) >= suite["minimum_distinct_authority_cases"]
    assert set(suite["normal_case_ids"]) <= frozen_ids
    assert set(suite["authority_case_ids"]) <= frozen_ids
    assert suite["case_policy"]["preserve_trace"] is True
    assert suite["case_policy"]["preserve_live_output"] is True
    assert suite["case_policy"]["preserve_reference"] is True
    assert "authority_availability" in suite["case_policy"]["allowed_variant_axes"]
    assert "compact_material_support" in suite["case_policy"]["allowed_variant_axes"]
    forbidden = set(suite["case_policy"]["forbidden_model_inputs"])
    assert {"expected_gate_status", "expected_authority_status", "reference_verdict", "quadrant_label"} <= forbidden
    # Reading/validating the suite must not rewrite the frozen source.
    assert hashlib.sha256(frozen_path.read_bytes()).digest() == hashlib.sha256(frozen_bytes).digest()


def test_expanded_authority_matrix_is_the_full_valid_cartesian_product_per_case():
    suite = json.loads((PROBES / "judge-authority-quadrants.json").read_text())
    report = build_report()
    expected_keys = _expected_combination_keys()
    rows_by_case = defaultdict(list)
    for row in report["rows"]:
        rows_by_case[row["case_id"]].append(row)

    assert report["counts"]["rows"] == suite["expected_row_count"]
    assert report["counts"]["distinct_cases"] == 12
    assert report["counts"]["distinct_combinations"] == suite["expected_rows_per_case"]
    assert len(expected_keys) == suite["expected_rows_per_case"]
    assert set(rows_by_case) == set(report["dimensions"]["case_ids"])
    assert all(count == suite["expected_rows_per_case"] for count in report["counts"]["rows_per_case"].values())
    for rows in rows_by_case.values():
        actual_keys = [_combination_key(row) for row in rows]
        assert len(actual_keys) == len(set(actual_keys))
        assert set(actual_keys) == expected_keys

    assert set(report["counts"]["final_status"]) == {"F", "NF", "NE"}
    assert set(report["counts"]["authority_enabled"]) == {"true", "false"}
    assert set(report["counts"]["authority_required"]) == {"true", "false"}
    assert report["counts"]["effectiveness"] == {
        "PASS": 336,
        "DETECTED_INVALID": 24,
    }


def test_expanded_authority_matrix_preserves_full_inputs_and_configuration():
    report = build_report()
    assert all(row["query_input"] for row in report["rows"])
    assert all(isinstance(row["live_output"], dict) for row in report["rows"])
    assert all("conditions" in row["live_output"] for row in report["rows"])
    assert all(set(row["config"]) == {
        "authority_enabled",
        "authority_required",
        "authority_availability",
        "compact_material_backed",
        "mock_resolution_status",
        "judge_seed_status",
    } for row in report["rows"])


def test_authority_disabled_or_not_required_never_calls_or_changes_judge_result():
    rows = [
        row for row in build_report()["rows"]
        if not row["config"]["authority_enabled"]
        or not row["config"]["authority_required"]
    ]
    assert len(rows) == 108
    assert all(row["authority_call_count"] == 0 for row in rows)
    assert all(row["authority_resolution"] is None for row in rows)
    assert all(row["final_status"] == row["initial_status"] for row in rows)
    assert all(row["gate_status"] == "not_applicable" for row in rows)
    assert all(row["gate_findings"] == [] for row in rows)


def test_available_authority_resolution_semantics_cross_all_seed_statuses():
    rows = [
        row for row in build_report()["rows"]
        if row["config"]["authority_enabled"]
        and row["config"]["authority_required"]
        and row["config"]["authority_availability"] == "available"
    ]
    assert len(rows) == 180
    assert all(row["authority_call_count"] == 1 for row in rows)
    assert all(row["gate_status"] == "passed" for row in rows)
    assert all(row["gate_findings"] == [] for row in rows)

    observed = Counter(
        (row["authority_resolution"], row["initial_status"], row["final_status"])
        for row in rows
    )
    for resolution_status in RESOLUTION_STATUSES:
        for initial_status in ("F", "NF", "NE"):
            if resolution_status == "contradicted" and initial_status == "F":
                expected_final = "NE"
            elif resolution_status in {"unresolved", "ungoverned", "gap_only"}:
                expected_final = "NE"
            else:
                expected_final = initial_status
            assert observed[(resolution_status, initial_status, expected_final)] == 12


def test_unavailable_authority_distinguishes_sufficient_material_from_real_gap():
    rows = [
        row for row in build_report()["rows"]
        if row["config"]["authority_enabled"]
        and row["config"]["authority_required"]
        and row["config"]["authority_availability"] == "unavailable"
    ]
    sufficient = [row for row in rows if row["config"]["compact_material_backed"]]
    gaps = [row for row in rows if not row["config"]["compact_material_backed"]]

    assert len(sufficient) == 36
    assert all(row["authority_call_count"] == 0 for row in sufficient)
    assert all(row["final_status"] == row["initial_status"] for row in sufficient)
    assert all(row["gate_status"] == "passed" for row in sufficient)
    assert all(row["gate_findings"] == [] for row in sufficient)

    assert len(gaps) == 36
    assert all(row["authority_call_count"] == 0 for row in gaps)
    assert all(row["gate_status"] == "failed" for row in gaps)
    assert all(row["gate_findings"] == ["availability_miss"] for row in gaps)
    assert Counter(row["effectiveness"] for row in gaps) == {
        "DETECTED_INVALID": 24,
        "PASS": 12,
    }
    assert all(
        row["effectiveness"] == ("PASS" if row["initial_status"] == "NE" else "DETECTED_INVALID")
        for row in gaps
    )


def test_historical_authority_gate_replay_meets_frozen_thresholds():
    from impl.projects.client_search.draft.probes.judge_authority_gate_replay import run_replay

    report = run_replay(PROBES / "judge-authority-gate-replay.json")
    score = report["score"]
    assert score["status"] == "passed"
    assert score["dirty_recall"] >= 0.90
    assert score["clean_false_positives"] <= 1
    assert score["actionable_finding_rate"] == 1.0
    assert score["boundary_observation_count"] >= 1
