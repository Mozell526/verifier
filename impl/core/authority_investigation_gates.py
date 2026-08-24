"""Deterministic Authority gates for Draft Investigate/Solidify handoff.

The artifact validated here is an investigation-time claim index.  It is not a
runtime resolution cache: it records source claims, conflicts, and coverage-gap
bindings so probes can prove the evidence space is consumable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .hashing import stable_sha256

CLAIM_INDEX_SCHEMA_VERSION = 1
CLAIM_INDEX_RELATIVE_PATH = "docs/authority-claims.json"
_AMORPHOUS_REQUIRED_EVIDENCE = re.compile(
    r"^\s*(?:需要更多(?:信息|资料|证据)|补充资料|more (?:information|evidence))\s*$",
    re.IGNORECASE,
)


def _text(value: Any, owner: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} must be non-empty text")
    return value.strip()


def _strings(value: Any, owner: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{owner} must be a JSON array")
    result = [_text(item, f"{owner}[{index}]") for index, item in enumerate(value)]
    if not allow_empty and not result:
        raise ValueError(f"{owner} must be non-empty")
    return result


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def load_and_validate_authority_claim_index(
    path: Path,
    *,
    evidence_ref_ids: set[str],
    coverage_gaps: Mapping[str, Any],
) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError("Authority claim index must be a JSON object")
    allowed = {"schema_version", "claims", "resolutions", "gap_bindings"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Authority claim index contains unknown field: {unknown[0]}")
    if raw.get("schema_version") != CLAIM_INDEX_SCHEMA_VERSION:
        raise ValueError(
            f"Authority claim index schema_version must be {CLAIM_INDEX_SCHEMA_VERSION}"
        )

    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list) or not claims_raw:
        raise ValueError("Authority claim index claims must be a non-empty array")
    claims: list[dict[str, Any]] = []
    claim_ids: set[str] = set()
    subjects: dict[str, list[dict[str, Any]]] = {}
    for index, item in enumerate(claims_raw):
        owner = f"claims[{index}]"
        if not isinstance(item, Mapping):
            raise TypeError(f"{owner} must be an object")
        allowed_claim = {
            "claim_id", "subject_id", "subject_kind", "conclusion_kind", "claim",
            "conditions", "source_ref_ids",
        }
        extra = sorted(set(item) - allowed_claim)
        if extra:
            raise ValueError(f"{owner} contains unknown field: {extra[0]}")
        claim_id = _text(item.get("claim_id"), f"{owner}.claim_id")
        if claim_id in claim_ids:
            raise ValueError(f"duplicate Authority claim_id: {claim_id}")
        claim_ids.add(claim_id)
        source_ref_ids = _strings(item.get("source_ref_ids"), f"{owner}.source_ref_ids")
        unknown_refs = sorted(set(source_ref_ids) - evidence_ref_ids)
        if unknown_refs:
            raise ValueError(f"{owner} references unknown EvidenceRef: {', '.join(unknown_refs)}")
        conditions = _strings(item.get("conditions", []), f"{owner}.conditions", allow_empty=True)
        claim = {
            "claim_id": claim_id,
            "subject_id": _text(item.get("subject_id"), f"{owner}.subject_id"),
            "subject_kind": _text(item.get("subject_kind"), f"{owner}.subject_kind"),
            "conclusion_kind": _text(
                item.get("conclusion_kind"), f"{owner}.conclusion_kind"
            ),
            "claim": _text(item.get("claim"), f"{owner}.claim"),
            "conditions": conditions,
            "source_ref_ids": source_ref_ids,
        }
        claims.append(claim)
        subjects.setdefault(claim["subject_id"], []).append(claim)

    resolutions: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw.get("resolutions") or []):
        owner = f"resolutions[{index}]"
        if not isinstance(item, Mapping):
            raise TypeError(f"{owner} must be an object")
        subject_id = _text(item.get("subject_id"), f"{owner}.subject_id")
        if subject_id in resolutions:
            raise ValueError(f"duplicate Authority subject resolution: {subject_id}")
        basis = _strings(item.get("basis_source_ref_ids"), f"{owner}.basis_source_ref_ids")
        unknown_refs = sorted(set(basis) - evidence_ref_ids)
        if unknown_refs:
            raise ValueError(f"{owner} references unknown EvidenceRef: {', '.join(unknown_refs)}")
        resolutions[subject_id] = {
            "subject_id": subject_id,
            "statement": _text(item.get("statement"), f"{owner}.statement"),
            "reason": _text(item.get("reason"), f"{owner}.reason"),
            "basis_source_ref_ids": basis,
        }

    gap_bindings: dict[str, str] = {}
    for index, item in enumerate(raw.get("gap_bindings") or []):
        owner = f"gap_bindings[{index}]"
        if not isinstance(item, Mapping):
            raise TypeError(f"{owner} must be an object")
        subject_id = _text(item.get("subject_id"), f"{owner}.subject_id")
        gap_id = _text(item.get("gap_id"), f"{owner}.gap_id")
        if subject_id in gap_bindings:
            raise ValueError(f"duplicate Authority gap binding: {subject_id}")
        if gap_id not in coverage_gaps:
            raise ValueError(f"{owner} references unknown CoverageGap: {gap_id}")
        required = list(getattr(coverage_gaps[gap_id], "required_evidence", ()) or ())
        if not required or any(_AMORPHOUS_REQUIRED_EVIDENCE.match(item) for item in required):
            raise ValueError(f"CoverageGap[{gap_id}].required_evidence must be specific")
        gap_bindings[subject_id] = gap_id

    conflicts: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    for subject_id in sorted(subjects):
        subject_claims = subjects[subject_id]
        conclusions = {_normalized(item["claim"]) for item in subject_claims}
        condition_sets = [
            frozenset(_normalized(value) for value in item["conditions"])
            for item in subject_claims
        ]
        source_refs = sorted({ref for item in subject_claims for ref in item["source_ref_ids"]})
        conflict_kind: str | None = None
        if len(conclusions) > 1:
            # Empty conditions are global and therefore overlap every scoped claim.
            # Equal condition sets are known to overlap. Different non-empty sets may
            # be mutually exclusive, so retain them as a potential conflict instead
            # of pretending that a deterministic validator understood business scope.
            known_overlap = any(
                not left or not right or left == right
                for index, left in enumerate(condition_sets)
                for right in condition_sets[index + 1 :]
            )
            conflict_kind = "conflict" if known_overlap else "potential_conflict"
        if conflict_kind is not None:
            conflicts.append({
                "subject_id": subject_id,
                "kind": conflict_kind,
                "claim_ids": [c["claim_id"] for c in subject_claims],
            })
            if subject_id in resolutions:
                basis = resolutions[subject_id]["basis_source_ref_ids"]
                if not set(basis).intersection(source_refs):
                    raise ValueError(
                        "Authority subject resolution requires decisive EvidenceRef "
                        f"from the subject claims: {subject_id}"
                    )
                status = "resolved"
                required_evidence: list[str] = []
            elif subject_id in gap_bindings:
                status = "unresolved"
                gap = coverage_gaps[gap_bindings[subject_id]]
                basis = list(getattr(gap, "basis_source_ref_ids", ()) or ())
                required_evidence = list(getattr(gap, "required_evidence", ()) or ())
            else:
                raise ValueError(
                    f"Authority claim {conflict_kind} has neither resolution nor coverage gap: {subject_id}"
                )
        else:
            status = "resolved"
            basis = source_refs
            required_evidence = []
        probes.append({
            "probe_id": f"authority-probe-{stable_sha256(subject_id)[:12]}",
            "subject_id": subject_id,
            "expected_status": status,
            "basis_evidence_ref_ids": basis,
            "required_evidence": required_evidence,
        })

    unused_resolutions = sorted(set(resolutions) - set(subjects))
    unused_bindings = sorted(set(gap_bindings) - set(subjects))
    if unused_resolutions or unused_bindings:
        raise ValueError(
            "Authority claim index has bindings for unknown subjects: "
            + ", ".join(unused_resolutions + unused_bindings)
        )

    return {
        "schema_version": CLAIM_INDEX_SCHEMA_VERSION,
        "claim_count": len(claims),
        "subject_count": len(subjects),
        "conflict_count": len(conflicts),
        "resolved_conflict_count": sum(
            1 for item in conflicts if item["subject_id"] in resolutions
        ),
        "unresolved_conflict_count": sum(
            1 for item in conflicts if item["subject_id"] in gap_bindings
        ),
        "potential_conflict_count": sum(
            1 for item in conflicts if item["kind"] == "potential_conflict"
        ),
        "claims_sha256": stable_sha256(claims),
        "probes": probes,
    }
