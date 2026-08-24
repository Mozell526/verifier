"""Deterministic Solidify hand-off receipt for Judge/Mock Draft candidates.

The receipt is an internal Draft audit artifact. It does not alter public RoleResult,
ContextUnit, Tool, InvestigationManifest, or Draft Loop schemas.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .investigation import validate_investigation_package
from .investigation_validation import require_investigation_validation_receipt
from .portable_artifact import (
    project_artifact_repository_root,
    write_active_artifact,
    write_portable_export,
)
from .project_loader import (
    load_adapter,
    load_project_role_instance,
    resolve_project_package_root,
    resolve_project_source_root,
    resolve_role_assets,
)


SOLIDIFY_RECEIPT_VERSION = 1
_SUPPORTED_ROLES = {"judge", "mock"}
_SYNTHETIC_ASSET_IDS = {"candidate_role"}


def solidify_receipt_path(spec: Any, role: str, *, must_exist: bool = True) -> Path:
    accessor = getattr(spec, "solidify_receipt_path", None)
    if callable(accessor):
        return accessor(role, must_exist=must_exist)
    path = (
        resolve_project_package_root(spec, must_exist=True)
        / "draft"
        / ".state"
        / role
        / "solidify.json"
    )
    if must_exist and not path.is_file():
        raise FileNotFoundError(f"Draft Solidify receipt not found: {path}")
    return path



def write_solidify_probe_result(path: Path, payload: Mapping[str, Any]) -> Path:
    """Persist a solidify smoke result through its registered artifact family."""
    target = Path(path)
    repository_root = project_artifact_repository_root(target)
    if repository_root is None:
        return write_portable_export(target, payload)
    return write_active_artifact(
        "draft_solidify_probe",
        target,
        payload,
        repository_root=repository_root,
    )

def write_solidify_receipt(
    spec: Any,
    role: str,
    *,
    mappings: Sequence[Mapping[str, Any]],
    runtime_observables: Sequence[Mapping[str, Any]],
) -> Path:
    normalized_role = _role(role)
    snapshot = _current_snapshot(spec, normalized_role)
    observables = _validate_runtime_observables(
        runtime_observables,
        available_asset_ids=set(snapshot["available_asset_ids"]),
        project_root=resolve_project_package_root(spec, must_exist=True),
    )
    normalized_mappings = _validate_mappings(
        mappings,
        required_source_ids=set(snapshot["required_source_ids"]),
        available_asset_ids=set(snapshot["available_asset_ids"]),
        observables=observables,
    )
    _validate_authority_runtime_replay(
        observables,
        project_root=resolve_project_package_root(spec, must_exist=True),
        probes=snapshot.get("authority_probes") or [],
    )
    payload = {
        "schema_version": SOLIDIFY_RECEIPT_VERSION,
        "project_id": spec.project_id,
        "role": normalized_role,
        "manifest_sha256": snapshot["manifest_sha256"],
        "role_contract_sha256": snapshot["role_contract_sha256"],
        "candidate_role_sha256": snapshot["candidate_role_sha256"],
        "asset_fingerprints": snapshot["asset_fingerprints"],
        "required_source_ids": snapshot["required_source_ids"],
        "mappings": normalized_mappings,
        "runtime_observables": observables,
    }
    path = solidify_receipt_path(spec, normalized_role, must_exist=False)
    return write_active_artifact(
        "draft_solidify_receipt",
        path,
        payload,
        repository_root=spec.verifier_root_path(),
    )


def require_solidify_receipt(
    spec: Any,
    role: str,
    *,
    business_source_staleness_policy: str = "strict",
) -> Mapping[str, Any] | None:
    """Require a fresh receipt when the selected Judge/Mock has Investigation assets.

    A project with no configured Investigation asset stays on the same unified path
    with an empty ContextUnit set; it does not acquire a separate legacy branch.
    """
    normalized_role = _role(role)
    selected = resolve_role_assets(spec, normalized_role, use_candidate=True)
    investigation_assets = [
        item for item in selected if item["mapping"].kind == "investigation"
    ]
    if not investigation_assets:
        return None
    if len(investigation_assets) != 1:
        raise ValueError(
            f"Draft role={normalized_role} requires exactly one investigation asset; "
            f"found={len(investigation_assets)}"
        )

    path = solidify_receipt_path(spec, normalized_role)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError(f"Draft Solidify receipt must be an object: {path}")
    allowed = {
        "schema_version",
        "project_id",
        "role",
        "manifest_sha256",
        "role_contract_sha256",
        "candidate_role_sha256",
        "asset_fingerprints",
        "required_source_ids",
        "mappings",
        "runtime_observables",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Draft Solidify receipt contains unknown field: {unknown[0]}")
    schema_version = raw.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != SOLIDIFY_RECEIPT_VERSION
    ):
        raise ValueError(f"unsupported Draft Solidify receipt version: {path}")
    if raw.get("project_id") != spec.project_id or raw.get("role") != normalized_role:
        raise ValueError(f"Draft Solidify receipt identity mismatch: {path}")

    current = _current_snapshot(
        spec,
        normalized_role,
        business_source_staleness_policy=business_source_staleness_policy,
    )
    for key in (
        "manifest_sha256",
        "role_contract_sha256",
        "candidate_role_sha256",
        "asset_fingerprints",
        "required_source_ids",
    ):
        if raw.get(key) != current[key]:
            raise ValueError(
                f"Draft Solidify receipt is stale: {key} changed. "
                "候选已在 solidify 之外变更，先重跑 scripts/solidify.py 更新收据"
            )
    observables = _validate_runtime_observables(
        raw.get("runtime_observables"),
        available_asset_ids=set(current["available_asset_ids"]),
        project_root=resolve_project_package_root(spec, must_exist=True),
    )
    _validate_mappings(
        raw.get("mappings"),
        required_source_ids=set(current["required_source_ids"]),
        available_asset_ids=set(current["available_asset_ids"]),
        observables=observables,
    )
    _validate_authority_runtime_replay(
        observables,
        project_root=resolve_project_package_root(spec, must_exist=True),
        probes=current.get("authority_probes") or [],
    )
    result = dict(raw)
    result["runtime_staleness"] = current["runtime_staleness"]
    return result


def _current_snapshot(
    spec: Any,
    role: str,
    *,
    business_source_staleness_policy: str = "strict",
) -> dict[str, Any]:
    require_investigation_validation_receipt(
        spec,
        role,
        business_source_staleness_policy=business_source_staleness_policy,
    )
    selected = resolve_role_assets(spec, role, use_candidate=True)
    investigations = [item for item in selected if item["mapping"].kind == "investigation"]
    if len(investigations) != 1:
        raise ValueError(
            f"Draft role={role} requires exactly one enabled investigation package; "
            f"found={len(investigations)}"
        )
    project_root = resolve_project_package_root(spec, must_exist=True)
    source_root = resolve_project_source_root(spec) if spec.has_business_source else None
    tool_aliases = {
        str(item["mapping"].production_path): Path(item["path"])
        for item in selected
        if item["mapping"].kind == "tool" and item["available"]
    }
    result = validate_investigation_package(
        Path(investigations[0]["path"]),
        project_root=project_root,
        expected_project_id=spec.project_id,
        expected_role=role,
        tool_module_overrides=tool_aliases,
        source_root=source_root,
        business_source_staleness_policy=business_source_staleness_policy,
    )
    contract_path = Path(result["role_contract"]["path"])
    _validate_judge_business_contract_metadata(
        role=role,
        contract_path=contract_path,
        selected_assets=selected,
    )
    candidate_path = spec.role_draft_path(role, must_exist=True)
    if candidate_path is None:
        raise FileNotFoundError(f"Draft role={role} has no configured candidate module")
    implementation = load_project_role_instance(spec, role, load_adapter(spec))
    if implementation is None:
        raise TypeError(f"Draft role={role} candidate did not instantiate")

    role_contract_summary = result["role_contract"]
    required_source_ids = _required_contract_source_ids(role, role_contract_summary)
    authority_report = role_contract_summary.get("authority_report")
    if isinstance(authority_report, Mapping):
        required_source_ids.extend(_required_authority_source_ids(authority_report))
        required_source_ids = sorted(set(required_source_ids))
    asset_fingerprints = [
        {
            "asset_id": item["mapping"].asset_id,
            "kind": item["mapping"].kind,
            "sha256": _path_sha256(Path(item["path"])),
        }
        for item in selected
        if item["available"]
    ]
    asset_fingerprints.sort(key=lambda item: item["asset_id"])
    return {
        "manifest_sha256": result["manifest_sha256"],
        "role_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "candidate_role_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "asset_fingerprints": asset_fingerprints,
        "required_source_ids": required_source_ids,
        "authority_probes": (
            list(authority_report.get("authority_claim_gate", {}).get("probes") or [])
            if isinstance(authority_report, Mapping)
            else []
        ),
        "available_asset_ids": [
            item["mapping"].asset_id for item in selected if item["available"]
        ] + sorted(_SYNTHETIC_ASSET_IDS),
        "runtime_staleness": {
            "policy": business_source_staleness_policy,
            "source_revision": str(result.get("source_revision") or ""),
            "current_source_revision": str(result.get("current_source_revision") or ""),
            "source_revision_drifted": bool(result.get("source_revision_drifted")),
            "warnings": list(result.get("staleness_warnings") or []),
        },
    }


def _validate_judge_business_contract_metadata(
    *,
    role: str,
    contract_path: Path,
    selected_assets: Sequence[Mapping[str, Any]],
) -> None:
    """Prove that runtime Planning metadata is a Solidify projection, not a second truth."""

    if role != "judge":
        return
    from .schema.investigation_judge import load_judge_contract

    contract = load_judge_contract(contract_path)
    owners = [
        item
        for item in selected_assets
        if item["mapping"].asset_id == "judge_business_contract"
    ]
    if len(owners) != 1:
        raise ValueError(
            "Judge Solidify requires exactly one judge_business_contract asset"
        )
    metadata = dict(owners[0]["mapping"].metadata or {})
    expected_products = {
        str(item.expectation_id) for item in contract.business_expectations
    }
    expected_dimensions = {
        str(item.dimension_id) for item in contract.evaluation_dimensions
    }
    expected_links = {
        str(item.dimension_id): sorted(
            str(value) for value in item.expectation_ids
        )
        for item in contract.evaluation_dimensions
    }
    expected_scenarios = {
        str(item.expectation_id): str(item.use_scenario)
        for item in contract.business_expectations
    }
    actual_links = {
        str(key): sorted(str(value) for value in values)
        for key, values in (
            metadata.get("dimension_expectation_ids") or {}
        ).items()
    }
    if set(metadata.get("product_expectation_ids") or []) != expected_products:
        raise ValueError(
            "Judge business-contract product expectations drifted from Investigation"
        )
    if set(metadata.get("dimensions") or []) != expected_dimensions:
        raise ValueError(
            "Judge business-contract dimensions drifted from Investigation"
        )
    if actual_links != expected_links:
        raise ValueError(
            "Judge business-contract dimension links drifted from Investigation"
        )
    if dict(metadata.get("product_use_scenarios") or {}) != expected_scenarios:
        raise ValueError(
            "Judge business-contract use scenarios drifted from Investigation"
        )
    boundary = contract.live_boundary
    boundary_payload = {
        "live_role": boundary.live_role,
        "in_scope_responsibilities": list(
            boundary.in_scope_responsibilities
        ),
        "out_of_scope_responsibilities": list(
            boundary.out_of_scope_responsibilities
        ),
        "external_constraints": list(boundary.external_constraints),
    }
    expected_boundary_hash = hashlib.sha256(
        json.dumps(
            boundary_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if metadata.get("live_boundary_sha256") != expected_boundary_hash:
        raise ValueError(
            "Judge business-contract LiveBoundary drifted from Investigation"
        )


def _required_authority_source_ids(summary: Mapping[str, Any]) -> list[str]:
    """Minimal Solidify mapping surface for an Investigation Authority product.

    Keep the mapping coarse-grained: claim subjects remain inside the validated
    Claim Index and do not explode the public Solidify receipt.
    """
    claim_gate = summary.get("authority_claim_gate")
    if not isinstance(claim_gate, Mapping):
        raise ValueError("Authority Solidify requires a validated authority claim gate")
    if not claim_gate.get("claims_sha256") or not claim_gate.get("probes"):
        raise ValueError("Authority Solidify requires frozen claim hash and probes")
    required = [
        "authority-investigation-report",
        "authority-claim-index",
        "authority-search-load",
    ]
    if int(summary.get("coverage_gaps") or 0) > 0:
        required.append("authority-coverage-gaps")
    return sorted(required)


def _required_contract_source_ids(role: str, summary: Mapping[str, Any]) -> list[str]:
    if role == "judge":
        ids = ["live_boundary"]
        ids.extend(f"expectation:{value}" for value in summary.get("expectation_ids") or [])
        ids.extend(f"dimension:{value}" for value in summary.get("dimension_ids") or [])
    else:
        ids = [f"business_value:{value}" for value in summary.get("business_value_ids") or []]
        ids.extend(f"dimension:{value}" for value in summary.get("dimension_ids") or [])
        ids.extend(f"demand_space:{value}" for value in summary.get("demand_space_ids") or [])
    return sorted(ids)


def _validate_mappings(
    value: Any,
    *,
    required_source_ids: set[str],
    available_asset_ids: set[str],
    observables: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("Solidify mappings must be a non-empty list")
    observable_by_id = {str(item["observable_id"]): item for item in observables}
    normalized: list[dict[str, Any]] = []
    seen_mapping_ids: set[str] = set()
    covered_source_ids: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise TypeError(f"Solidify mappings[{index}] must be an object")
        allowed = {"mapping_id", "source_ids", "asset_ids", "runtime_observables"}
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise ValueError(f"Solidify mappings[{index}] contains unknown field: {unknown[0]}")
        mapping_id = _text(raw.get("mapping_id"), f"Solidify mappings[{index}].mapping_id")
        if mapping_id in seen_mapping_ids:
            raise ValueError(f"duplicate Solidify mapping_id: {mapping_id}")
        seen_mapping_ids.add(mapping_id)
        source_ids = _string_list(raw.get("source_ids"), f"Solidify mappings[{index}].source_ids")
        asset_ids = _string_list(raw.get("asset_ids"), f"Solidify mappings[{index}].asset_ids")
        observable_names = _string_list(
            raw.get("runtime_observables"),
            f"Solidify mappings[{index}].runtime_observables",
        )
        unknown_sources = sorted(set(source_ids) - required_source_ids)
        if unknown_sources:
            raise ValueError(
                "Solidify mapping references unknown contract source ID: "
                + ", ".join(unknown_sources)
            )
        unknown_assets = sorted(set(asset_ids) - available_asset_ids)
        if unknown_assets:
            raise ValueError(
                "Solidify mapping references unavailable asset ID: "
                + ", ".join(unknown_assets)
            )
        unknown_observables = sorted(set(observable_names) - set(observable_by_id))
        if unknown_observables:
            raise ValueError(
                "Solidify mapping references unknown runtime observable: "
                + ", ".join(unknown_observables)
            )
        observed_assets = {
            asset_id
            for name in observable_names
            for asset_id in observable_by_id[name]["observed_asset_ids"]
        }
        required_observed_assets = set(asset_ids) - _SYNTHETIC_ASSET_IDS
        missing_observation = sorted(required_observed_assets - observed_assets)
        if missing_observation:
            raise ValueError(
                f"Solidify mapping {mapping_id!r} assets absent from its runtime observables: "
                + ", ".join(missing_observation)
            )
        covered_source_ids.update(source_ids)
        normalized.append(
            {
                "mapping_id": mapping_id,
                "source_ids": source_ids,
                "asset_ids": asset_ids,
                "runtime_observables": observable_names,
            }
        )
    missing = sorted(required_source_ids - covered_source_ids)
    if missing:
        raise ValueError(
            "Solidify mappings do not cover required contract IDs: " + ", ".join(missing)
        )
    return normalized


def _validate_runtime_observables(
    value: Any,
    *,
    available_asset_ids: set[str],
    project_root: Path,
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("Solidify runtime_observables must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise TypeError(f"Solidify runtime_observables[{index}] must be an object")
        allowed = {"observable_id", "status", "evidence", "observed_asset_ids"}
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise ValueError(
                f"Solidify runtime_observables[{index}] contains unknown field: {unknown[0]}"
            )
        observable_id = _text(
            raw.get("observable_id"), f"runtime_observables[{index}].observable_id"
        )
        if observable_id in seen:
            raise ValueError(f"duplicate Solidify observable_id: {observable_id}")
        seen.add(observable_id)
        status = _text(raw.get("status"), f"runtime_observables[{index}].status")
        if status != "succeeded":
            raise ValueError(
                f"Solidify runtime observable did not succeed: {observable_id}: {status}"
            )
        evidence = _text(raw.get("evidence"), f"runtime_observables[{index}].evidence")
        evidence_path = Path(evidence.split("#", 1)[0])
        if evidence_path.is_absolute() or ".." in evidence_path.parts:
            raise ValueError(
                f"Solidify observable evidence must be a portable relative pointer: {evidence}"
            )
        physical_evidence = project_root / evidence_path
        if not physical_evidence.is_file():
            raise FileNotFoundError(
                f"Solidify runtime observable evidence does not exist: {physical_evidence}"
            )
        observed_asset_ids = _string_list(
            raw.get("observed_asset_ids"),
            f"runtime_observables[{index}].observed_asset_ids",
            allow_empty=True,
        )
        unknown_assets = sorted(set(observed_asset_ids) - available_asset_ids)
        if unknown_assets:
            raise ValueError(
                "Solidify runtime observable references unavailable asset ID: "
                + ", ".join(unknown_assets)
            )
        normalized.append(
            {
                "observable_id": observable_id,
                "status": status,
                "evidence": evidence,
                "observed_asset_ids": observed_asset_ids,
            }
        )
    return normalized


def _validate_authority_runtime_replay(
    observables: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
    probes: Sequence[Mapping[str, Any]],
) -> None:
    """Require real Authority Tool evidence when Investigation froze probes."""
    if not probes:
        return
    replay: Mapping[str, Any] | None = None
    for observable in observables:
        evidence_path = str(observable.get("evidence") or "").split("#", 1)[0]
        if not evidence_path:
            continue
        try:
            raw = json.loads((project_root / evidence_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        candidate = (raw.get("checks") or {}).get("authority_runtime_replay") if isinstance(raw, Mapping) else None
        if isinstance(candidate, Mapping):
            replay = candidate
            break
    if replay is None:
        raise ValueError(
            "Authority Runtime Replay missing: Solidify smoke must prove real authority.resolve "
            "calls for frozen Investigation probes; constructed AuthorityResolution is insufficient"
        )
    results = replay.get("probe_results")
    if not isinstance(results, list) or not results:
        raise ValueError("Authority Runtime Replay requires non-empty probe_results")
    by_subject = {
        str(item.get("subject_id")): item
        for item in results
        if isinstance(item, Mapping) and item.get("subject_id")
    }
    missing = sorted(str(item.get("subject_id")) for item in probes if str(item.get("subject_id")) not in by_subject)
    if missing:
        raise ValueError("Authority Runtime Replay missing frozen subjects: " + ", ".join(missing))
    statuses: set[str] = set()
    for probe in probes:
        subject_id = str(probe.get("subject_id"))
        result = by_subject[subject_id]
        if not str(result.get("tool_call_id") or "").startswith("authority."):
            raise ValueError(f"Authority Runtime Replay lacks real authority.resolve tool_call_id: {subject_id}")
        if not result.get("tool_audit_present") or not result.get("environment_snapshot_sha256"):
            raise ValueError(f"Authority Runtime Replay lacks Tool audit/snapshot: {subject_id}")
        actual = str(result.get("status") or "")
        expected = str(probe.get("expected_status") or "")
        if actual != expected:
            raise ValueError(
                f"Authority Runtime Replay status mismatch for {subject_id}: expected={expected}, actual={actual}"
            )
        statuses.add(actual)
    expected_statuses = {str(item.get("expected_status") or "") for item in probes}
    if {"resolved", "unresolved"}.issubset(expected_statuses) and not {"resolved", "unresolved"}.issubset(statuses):
        raise ValueError("Authority Runtime Replay must cover both resolved and unresolved probes")


def _path_sha256(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if not path.is_dir():
        raise FileNotFoundError(f"Solidify asset not found: {path}")
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        if "__pycache__" in child.parts or child.name.endswith((".pyc", ".sqlite3")):
            continue
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _role(role: str) -> str:
    normalized = str(role or "").strip()
    if normalized not in _SUPPORTED_ROLES:
        raise ValueError(
            f"Solidify receipt supports only Judge/Mock: {normalized or '<empty>'}"
        )
    return normalized


def _text(value: Any, owner: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} is required")
    return value.strip()


def _string_list(value: Any, owner: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{owner} must be a list of strings")
    if not value and not allow_empty:
        raise ValueError(f"{owner} must be non-empty")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise TypeError(f"{owner}[{index}] must be a non-empty string")
        result.append(item.strip())
    if len(set(result)) != len(result):
        raise ValueError(f"{owner} contains duplicate values")
    return result
