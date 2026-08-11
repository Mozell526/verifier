"""Business-source staleness public facility.

Implements spec/grill/staleness_public_facility.md: unified deterministic
handling of business-source drift for Draft experiments and frozen evidence.

Core ideas:
- A source change only "matters" through the consumers registered for it.
- Slice-level hash manifests locate *where* a file changed.
- Consumption modes route the disposition: key_live consumers absorb drift,
  positional frozen assets require a whole-generation rebuild, and frozen
  conclusions (material decisions) without dependency keys conservatively
  require point re-verification.
- strict/warn share one boundary function; only the disposition differs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from impl.core.schema.investigation import (
    SLICE_MODE_FIELD,
    SLICE_MODE_YAML_LIST_CHUNK,
    SLICE_MODE_YAML_MAPPING_FIELD,
)

# Consumption modes registered per EvidenceRef (metadata["consumption"]).
CONSUMPTION_KEY_LIVE = "key_live"
CONSUMPTION_POSITIONAL_FROZEN = "positional_frozen"
CONSUMPTION_FROZEN_CONCLUSION = "frozen_conclusion"
CONSUMPTION_MODES = {
    CONSUMPTION_KEY_LIVE,
    CONSUMPTION_POSITIONAL_FROZEN,
    CONSUMPTION_FROZEN_CONCLUSION,
}

_KEY_STABLE_MODES = {SLICE_MODE_FIELD, SLICE_MODE_YAML_MAPPING_FIELD}

# Routing dispositions for a drifted EvidenceRef.
ROUTING_CLEAN = "clean"
ROUTING_ABSORB = "absorb"
ROUTING_POSITIONAL_REBUILD = "positional_rebuild"
ROUTING_NEEDS_REVIEW = "needs_review"

_SLICE_KEY_FIELD = "field:"
_SLICE_KEY_CHUNK = "chunk:"

# 大材料门禁阈值：超过该字符数的业务源材料必须登记检索通道（key-index/
# 位置切片），否则禁止整块注入 Runtime 上下文。
DEFAULT_LARGE_MATERIAL_THRESHOLD_CHARS = 30000


class StalenessPolicyViolation(Exception):
    """Raised when a strict lifecycle hits un-closed business-source drift."""


@dataclass(frozen=True)
class SliceChange:
    slice_key: str
    expected_sha256: str
    actual_sha256: str


@dataclass
class RefDriftReport:
    ref_id: str
    declared_sha256: str = ""
    actual_sha256: str = ""
    file_changed: bool = False
    slice_changes: list[SliceChange] = field(default_factory=list)
    consumption: list[dict[str, str]] = field(default_factory=list)
    registered_consumption: bool = False
    decisions: list[str] = field(default_factory=list)
    dep_keyed_decisions: list[str] = field(default_factory=list)
    routing: str = ROUTING_CLEAN
    reason: str = ""
    affected_key_index_entries: list[str] = field(default_factory=list)
    affected_embedding_entries: list[str] = field(default_factory=list)
    affected_decisions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "declared_sha256": self.declared_sha256,
            "actual_sha256": self.actual_sha256,
            "file_changed": self.file_changed,
            "slice_changes": [
                {
                    "slice_key": change.slice_key,
                    "expected_sha256": change.expected_sha256,
                    "actual_sha256": change.actual_sha256,
                }
                for change in self.slice_changes
            ],
            "consumption": list(self.consumption),
            "registered_consumption": self.registered_consumption,
            "decisions": list(self.decisions),
            "dep_keyed_decisions": list(self.dep_keyed_decisions),
            "routing": self.routing,
            "reason": self.reason,
            "affected_key_index_entries": list(self.affected_key_index_entries),
            "affected_embedding_entries": list(self.affected_embedding_entries),
            "affected_decisions": list(self.affected_decisions),
        }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_consumption(value: Any) -> list[dict[str, str]]:
    """Validate and normalize metadata["consumption"] entries."""
    normalized: list[dict[str, str]] = []
    for item in value or []:
        if not isinstance(item, Mapping):
            raise ValueError("consumption entries must be objects")
        consumer = str(item.get("consumer") or "").strip()
        mode = str(item.get("mode") or "").strip()
        if not consumer:
            raise ValueError("consumption entry requires consumer")
        if mode not in CONSUMPTION_MODES:
            raise ValueError(
                f"unsupported consumption mode {mode!r}; expected one of {sorted(CONSUMPTION_MODES)}"
            )
        normalized.append({"consumer": consumer, "mode": mode})
    return normalized


def slice_entries(path: Path, slice_spec: Mapping[str, Any]) -> list[dict[str, str]]:
    """Project a sliced EvidenceRef into stable ``slice_key -> content`` entries.

    Mirrors authority_environment's materializers: field/yaml_mapping_field
    slices are keyed by field name (stable), yaml_list_chunk slices are keyed
    by position and therefore generation-bound.
    """
    import yaml

    mode = str(slice_spec.get("mode") or "").strip()
    with Path(path).open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return _slice_entries_from_document(document, slice_spec, mode)


def slice_entries_from_text(text: str, slice_spec: Mapping[str, Any]) -> list[dict[str, str]]:
    """Project slice entries from raw YAML text (e.g. a committed revision)."""
    import yaml

    document = yaml.safe_load(text)
    return _slice_entries_from_document(document, slice_spec, str(slice_spec.get("mode") or "").strip())


def _slice_entries_from_document(document: Any, slice_spec: Mapping[str, Any], mode: str) -> list[dict[str, str]]:
    if mode == SLICE_MODE_FIELD:
        list_key = str(slice_spec.get("list_key") or "").strip()
        field_key = str(slice_spec.get("field_key") or "").strip()
        carry = [str(key) for key in (slice_spec.get("carry") or []) if str(key).strip()]
        if not list_key or not field_key:
            raise ValueError("field slice spec requires list_key and field_key")
        if not isinstance(document, dict) or list_key not in document:
            raise ValueError(f"slice document lacks list key {list_key!r}")
        items = document[list_key]
        if not isinstance(items, list):
            raise ValueError(f"slice list key {list_key!r} is not a list")
        fields: dict[str, list[Any]] = {}
        for item in items:
            if not isinstance(item, dict) or not str(item.get(field_key) or "").strip():
                raise ValueError(f"slice item lacks field key {field_key!r}")
            fields.setdefault(str(item[field_key]).strip(), []).append(item)
        entries: list[dict[str, str]] = []
        for field_name in sorted(fields):
            slice_doc: dict[str, Any] = {list_key: fields[field_name]}
            for key in carry:
                if key in document:
                    slice_doc[key] = document[key]
            content = json.dumps(slice_doc, ensure_ascii=False, sort_keys=True, default=str)
            entries.append({
                "slice_key": f"{_SLICE_KEY_FIELD}{field_name}",
                "content": content,
            })
        return entries
    if mode == SLICE_MODE_YAML_MAPPING_FIELD:
        if not isinstance(document, dict) or not document:
            raise ValueError("yaml_mapping_field slice requires a non-empty mapping")
        entries = []
        for key, definition in sorted(document.items(), key=lambda item: str(item[0])):
            field_name = str(key).strip()
            content = json.dumps(
                {field_name: definition}, ensure_ascii=False, sort_keys=True, default=str
            )
            entries.append({
                "slice_key": f"{_SLICE_KEY_FIELD}{field_name}",
                "content": content,
            })
        return entries
    if mode == SLICE_MODE_YAML_LIST_CHUNK:
        root_key = str(slice_spec.get("root_key") or "").strip()
        list_key = str(slice_spec.get("list_key") or "").strip()
        chunk_size = int(slice_spec.get("chunk_size") or 256)
        if not root_key or not list_key:
            raise ValueError("yaml_list_chunk slice spec requires root_key and list_key")
        if not isinstance(document, dict) or not isinstance(document.get(root_key), dict):
            raise ValueError(f"slice document lacks mapping root {root_key!r}")
        values = document[root_key].get(list_key)
        if not isinstance(values, list):
            raise ValueError(f"slice root {root_key!r} lacks list key {list_key!r}")
        entries = []
        for chunk_index, offset in enumerate(range(0, len(values), chunk_size), start=1):
            chunk = values[offset : offset + chunk_size]
            content = json.dumps(
                {root_key: {list_key: chunk}},
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            entries.append({
                "slice_key": f"{_SLICE_KEY_CHUNK}{chunk_index}",
                "content": content,
            })
        return entries
    raise ValueError(f"unsupported slice mode {mode!r}")


def compute_slice_hashes(path: Path, slice_spec: Mapping[str, Any]) -> dict[str, str]:
    return {
        entry["slice_key"]: _sha256_text(entry["content"])
        for entry in slice_entries(path, slice_spec)
    }


def compute_slice_hashes_from_text(text: str, slice_spec: Mapping[str, Any]) -> dict[str, str]:
    return {
        entry["slice_key"]: _sha256_text(entry["content"])
        for entry in slice_entries_from_text(text, slice_spec)
    }


def material_decision_keys(manifest: Mapping[str, Any], ref_id: str) -> list[str]:
    """Derive material-decision keys referencing a ref from the manifest index."""
    keys: list[str] = []
    prefix = f"{ref_id}."
    for index in manifest.get("key_indexes") or []:
        if index.get("index_key") != "authority.material-decisions":
            continue
        for entry in index.get("entries") or []:
            key = str(entry.get("key") or "")
            if key.startswith(prefix):
                keys.append(key)
    return sorted(keys)


def evidence_navigation_entry_keys(manifest: Mapping[str, Any], ref_id: str) -> list[str]:
    prefix = f"evidence-navigation://{ref_id}/"
    keys: list[str] = []
    for index in manifest.get("key_indexes") or []:
        for entry in index.get("entries") or []:
            target = str(entry.get("target_ref") or "")
            if target.startswith(prefix):
                keys.append(str(entry.get("key") or ""))
    return sorted(keys)


def detect_ref_drift(
    *,
    ref_id: str,
    path: Path,
    declared_sha256: str = "",
    slice_spec: Mapping[str, Any] | None = None,
    declared_slice_hashes: Mapping[str, str] | None = None,
    consumption: Sequence[Mapping[str, str]] = (),
    decisions: Sequence[str] = (),
    dep_keyed_decisions: Sequence[str] = (),
    navigation_entry_keys: Sequence[str] = (),
    embedding_entry_keys: Sequence[str] = (),
) -> RefDriftReport:
    """Deterministically evaluate one EvidenceRef against the current file."""
    report = RefDriftReport(
        ref_id=ref_id,
        declared_sha256=str(declared_sha256 or ""),
    )
    report.actual_sha256 = file_sha256(path)
    report.file_changed = bool(declared_sha256) and report.actual_sha256 != declared_sha256
    try:
        report.consumption = normalize_consumption(consumption)
        report.registered_consumption = bool(report.consumption)
    except ValueError as exc:
        report.consumption = []
        report.registered_consumption = False
        report.routing = ROUTING_NEEDS_REVIEW
        report.reason = f"invalid consumption registration: {exc}"
        return report

    report.decisions = sorted(str(item) for item in decisions)
    report.dep_keyed_decisions = sorted(str(item) for item in dep_keyed_decisions)

    actual_slice_hashes: dict[str, str] = {}
    if slice_spec and declared_slice_hashes:
        mode = str(slice_spec.get("mode") or "").strip()
        if mode in _KEY_STABLE_MODES:
            actual_slice_hashes = compute_slice_hashes(path, slice_spec)
            for key, expected in sorted(declared_slice_hashes.items()):
                actual = actual_slice_hashes.get(key, "")
                if actual and actual != expected:
                    report.slice_changes.append(SliceChange(key, expected, actual))
            for key in sorted(set(actual_slice_hashes) - set(declared_slice_hashes)):
                report.slice_changes.append(SliceChange(key, "", actual_slice_hashes[key]))
            for key in sorted(set(declared_slice_hashes) - set(actual_slice_hashes)):
                report.slice_changes.append(SliceChange(key, declared_slice_hashes[key], ""))

    if not report.file_changed:
        report.routing = ROUTING_CLEAN
        report.reason = "file content unchanged"
        return report

    changed_keys = {change.slice_key for change in report.slice_changes}
    if report.slice_changes:
        report.affected_key_index_entries = sorted(navigation_entry_keys)
        report.affected_embedding_entries = sorted(embedding_entry_keys)
    else:
        report.affected_key_index_entries = sorted(navigation_entry_keys) if report.file_changed else []
        report.affected_embedding_entries = sorted(embedding_entry_keys) if report.file_changed else []

    if report.decisions:
        if report.dep_keyed_decisions:
            # With dependency keys only decisions covering changed slices are affected.
            affected = []
            for decision_key in report.decisions:
                dep_keys = _dep_keys_for_decision(decision_key, dep_keyed_decisions)
                if dep_keys is None or dep_keys & changed_keys:
                    affected.append(decision_key)
            report.affected_decisions = sorted(affected)
        else:
            report.affected_decisions = list(report.decisions)

    modes = {str(item.get("mode") or "") for item in report.consumption}
    if not report.registered_consumption:
        report.routing = ROUTING_NEEDS_REVIEW
        report.reason = "no registered consumers; fail-closed"
    elif report.affected_decisions:
        report.routing = ROUTING_NEEDS_REVIEW
        report.reason = "affected material decisions require point re-verification"
    elif CONSUMPTION_POSITIONAL_FROZEN in modes:
        report.routing = ROUTING_POSITIONAL_REBUILD
        report.reason = "positional frozen consumer; whole-generation rebuild required"
    elif modes.issubset({CONSUMPTION_KEY_LIVE}):
        report.routing = ROUTING_ABSORB
        report.reason = "all consumers are key_live; drift is auto-absorbed"
    else:
        report.routing = ROUTING_NEEDS_REVIEW
        report.reason = "mixed consumption modes without positional rebuild; conservative"
    return report


def _dep_keys_for_decision(decision_key: str, dep_keyed_decisions: Sequence[str]) -> set[str] | None:
    """Map a decision key to its dependency slice keys, or None when unkeyed."""
    for item in dep_keyed_decisions:
        if str(item).startswith(f"{decision_key}:"):
            return set(str(item).split(":", 1)[1].split(","))
    return None


def apply_staleness_policy(
    report: RefDriftReport,
    policy: str,
) -> dict[str, Any]:
    """Shared strict/warn boundary. strict raises unless drift is closed.

    ``warn`` returns an informational warning record for runtime audit; ``strict``
    raises StalenessPolicyViolation for any non-clean routing.
    """
    if policy not in {"strict", "warn"}:
        raise ValueError("business_source_staleness_policy must be one of: strict, warn")
    if report.routing == ROUTING_CLEAN:
        return {"policy": policy, "routing": ROUTING_CLEAN, "warnings": []}
    record = {
        "policy": policy,
        "routing": report.routing,
        "reason": report.reason,
        "report": report.as_dict(),
    }
    if policy == "warn":
        return {"policy": policy, "routing": report.routing, "warnings": [record]}
    raise StalenessPolicyViolation(
        f"business-source drift requires closure under strict policy: "
        f"ref={report.ref_id} routing={report.routing} reason={report.reason}"
    )


def build_audit_record(
    *,
    ref_id: str,
    action: str,
    report: RefDriftReport,
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one atomic-refresh / drift audit entry for the global ledger."""
    return {
        "ref_id": ref_id,
        "action": action,
        "routing": report.routing,
        "declared_sha256": report.declared_sha256,
        "actual_sha256": report.actual_sha256,
        "slice_changes": [change.slice_key for change in report.slice_changes],
        "affected_decisions": list(report.affected_decisions),
        "affected_key_index_entries": list(report.affected_key_index_entries),
        "affected_embedding_entries": list(report.affected_embedding_entries),
        "outcome": outcome,
    }


def audit_large_materials_without_retrieval_channel(
    manifest: Any,
    source_root: Path,
    threshold_chars: int = DEFAULT_LARGE_MATERIAL_THRESHOLD_CHARS,
    declared_sources: Mapping[str, Path] | None = None,
) -> list[dict[str, Any]]:
    """确定性门禁：超过大小阈值的业务源材料必须登记检索通道。

    材料资产全量超过 threshold_chars 且未在 manifest metadata.consumption
    登记任何消费通道（key_live/positional_frozen）时，Runtime 不得整块注入；
    调查层必须先补 key-index/切片再消费。大材料靠人工记得过滤/截断是第二真相
    源风险，本检查把它变成门禁驱动。
    """
    findings: list[dict[str, Any]] = []
    refs = getattr(manifest, "evidence_refs", None)
    if refs is None and isinstance(manifest, Mapping):
        refs = manifest.get("evidence_refs") or []
    registered_locations: set[str] = set()
    for ref in refs or []:
        location = getattr(ref, "location_ref", None) or (ref.get("location") or {})
        raw_scope = getattr(location, "location_scope", None) or location.get("location_scope") or ""
        scope = str(getattr(raw_scope, "value", None) or "") if not isinstance(raw_scope, str) else raw_scope
        relative = str(getattr(location, "location", None) or location.get("location") or "").strip()
        if scope != "business_source":
            continue
        if not relative:
            continue
        registered_locations.add(relative)
        ref_id = str(getattr(ref, "ref_id", None) or ref.get("ref_id") or "").strip()
        metadata = ref.metadata if isinstance(getattr(ref, "metadata", None), dict) else (ref.get("metadata") or {})
        path = Path(source_root) / relative
        if not path.is_file():
            findings.append({
                "ref_id": ref_id,
                "source": relative,
                "size_chars": None,
                "threshold_chars": threshold_chars,
                "retrieval_channel": None,
                "problem": "business source material declared in manifest is missing on disk",
                "severity": "high",
            })
            continue
        size = len(path.read_text(encoding="utf-8", errors="replace"))
        if size <= threshold_chars:
            continue
        consumption = metadata.get("consumption") or []
        if consumption:
            continue
        findings.append({
            "ref_id": ref_id,
            "source": relative,
            "size_chars": size,
            "threshold_chars": threshold_chars,
            "retrieval_channel": None,
            "problem": "business source material exceeds the size threshold without a registered retrieval channel",
            "remediation": "register a key-index/positional consumption channel in manifest metadata.consumption before Runtime injection; do not inject the material whole or truncated",
            "severity": "high",
        })
    # 门禁盲区补漏：project.yaml 声明的业务源若未登记进调查 manifest，
    # 漂移检测与大材料门禁都覆盖不到；被声明且超阈值的大文件必须报出。
    for logical_name, path in (declared_sources or {}).items():
        path = Path(path)
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(source_root).as_posix()
        except ValueError:
            continue
        if rel in registered_locations:
            continue
        size = len(path.read_text(encoding="utf-8", errors="replace"))
        if size <= threshold_chars:
            continue
        findings.append({
            "ref_id": None,
            "logical_name": logical_name,
            "source": rel,
            "size_chars": size,
            "threshold_chars": threshold_chars,
            "retrieval_channel": None,
            "problem": "declared business source material is large but not registered in the investigation manifest",
            "remediation": "register the material in the investigation manifest with a retrieval consumption channel (key_live/positional_frozen) before Runtime consumption",
            "severity": "high",
        })
    return findings
