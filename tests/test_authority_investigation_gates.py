import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from impl.core.authority_investigation_gates import (
    load_and_validate_authority_claim_index,
)


def _claim(claim_id: str, statement: str, source: str, *, conditions=None):
    return {
        "claim_id": claim_id,
        "subject_id": "subject:one",
        "subject_kind": "business_rule",
        "conclusion_kind": "definition",
        "claim": statement,
        "conditions": list(conditions or []),
        "source_ref_ids": [source],
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "authority-claims.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _gap(required=("Load the owning policy revision for subject:one",), basis=("source-a",)):
    return SimpleNamespace(required_evidence=required, basis_source_ref_ids=basis)


def test_single_claim_builds_resolved_probe(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [_claim("claim-a", "Value A is valid", "source-a")],
        "resolutions": [],
        "gap_bindings": [],
    })

    result = load_and_validate_authority_claim_index(
        path, evidence_ref_ids={"source-a"}, coverage_gaps={}
    )

    assert result["conflict_count"] == 0
    assert result["probes"][0]["expected_status"] == "resolved"
    assert result["probes"][0]["basis_evidence_ref_ids"] == ["source-a"]


def test_conflict_with_specific_gap_builds_unresolved_probe(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [
            _claim("claim-a", "Value A is valid", "source-a"),
            _claim("claim-b", "Value B is valid", "source-b"),
        ],
        "resolutions": [],
        "gap_bindings": [{"subject_id": "subject:one", "gap_id": "gap-one"}],
    })

    result = load_and_validate_authority_claim_index(
        path,
        evidence_ref_ids={"source-a", "source-b"},
        coverage_gaps={"gap-one": _gap()},
    )

    assert result["conflict_count"] == 1
    assert result["unresolved_conflict_count"] == 1
    assert result["probes"][0]["expected_status"] == "unresolved"
    assert result["probes"][0]["required_evidence"]


def test_conflict_without_resolution_or_gap_is_rejected(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [
            _claim("claim-a", "Value A is valid", "source-a"),
            _claim("claim-b", "Value B is valid", "source-b"),
        ],
        "resolutions": [],
        "gap_bindings": [],
    })

    with pytest.raises(ValueError, match="neither resolution nor coverage gap"):
        load_and_validate_authority_claim_index(
            path, evidence_ref_ids={"source-a", "source-b"}, coverage_gaps={}
        )


def test_resolution_requires_decisive_subject_evidence(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [
            _claim("claim-a", "Value A is valid", "source-a"),
            _claim("claim-b", "Value B is valid", "source-b"),
        ],
        "resolutions": [{
            "subject_id": "subject:one",
            "statement": "Value A governs",
            "reason": "A separate note says so",
            "basis_source_ref_ids": ["unrelated-source"],
        }],
        "gap_bindings": [],
    })

    with pytest.raises(ValueError, match="decisive EvidenceRef"):
        load_and_validate_authority_claim_index(
            path,
            evidence_ref_ids={"source-a", "source-b", "unrelated-source"},
            coverage_gaps={},
        )


def test_unknown_evidence_ref_is_rejected(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [_claim("claim-a", "Value A is valid", "missing-source")],
        "resolutions": [],
        "gap_bindings": [],
    })

    with pytest.raises(ValueError, match="unknown EvidenceRef"):
        load_and_validate_authority_claim_index(
            path, evidence_ref_ids={"source-a"}, coverage_gaps={}
        )


def test_amorphous_gap_required_evidence_is_rejected(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [
            _claim("claim-a", "Value A is valid", "source-a"),
            _claim("claim-b", "Value B is valid", "source-b"),
        ],
        "resolutions": [],
        "gap_bindings": [{"subject_id": "subject:one", "gap_id": "gap-one"}],
    })

    with pytest.raises(ValueError, match="required_evidence must be specific"):
        load_and_validate_authority_claim_index(
            path,
            evidence_ref_ids={"source-a", "source-b"},
            coverage_gaps={"gap-one": _gap(required=("需要更多资料",))},
        )


def test_binding_for_unknown_subject_is_rejected(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [_claim("claim-a", "Value A is valid", "source-a")],
        "resolutions": [],
        "gap_bindings": [{"subject_id": "subject:missing", "gap_id": "gap-one"}],
    })

    with pytest.raises(ValueError, match="bindings for unknown subjects"):
        load_and_validate_authority_claim_index(
            path,
            evidence_ref_ids={"source-a"},
            coverage_gaps={"gap-one": _gap()},
        )


def test_different_nonempty_conditions_are_potential_conflict(tmp_path: Path):
    path = _write(tmp_path, {
        "schema_version": 1,
        "claims": [
            _claim("claim-a", "Value A is valid", "source-a", conditions=["channel is web"]),
            _claim("claim-b", "Value B is valid", "source-b", conditions=["channel is branch"]),
        ],
        "resolutions": [],
        "gap_bindings": [{"subject_id": "subject:one", "gap_id": "gap-one"}],
    })

    result = load_and_validate_authority_claim_index(
        path,
        evidence_ref_ids={"source-a", "source-b"},
        coverage_gaps={"gap-one": _gap()},
    )

    assert result["potential_conflict_count"] == 1
    assert result["probes"][0]["expected_status"] == "unresolved"
