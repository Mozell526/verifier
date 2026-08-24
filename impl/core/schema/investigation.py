from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ..path_contract import LogicalPathRef
from ..portable_artifact import (
    project_artifact_repository_root,
    write_active_artifact,
    write_portable_export,
)
from .base import to_dict
from .evidence import EvidenceRef
from .investigation_key_index import (
    InvestigationKeyIndex,
    validate_investigation_key_indexes,
)


INVESTIGATION_SCHEMA_VERSION = 2
SUPPORTED_INVESTIGATION_SCHEMA_VERSIONS = {1, 2}
MAX_INLINE_EVIDENCE_PAYLOAD_BYTES = 16_384

# 业务源切片投影模式的协议固定词汇（metadata.slice.mode / key-index 支撑门禁 /
# staleness 路由共用同一口径，勿在别处再硬编码字符串）。
SLICE_MODE_FIELD = "field"
SLICE_MODE_YAML_MAPPING_FIELD = "yaml_mapping_field"
SLICE_MODE_YAML_LIST_CHUNK = "yaml_list_chunk"

# 声明了切片的资料按粒度物化为多个 Evidence 单元；值级/块级检索必须由
# key-index 支撑，避免把全量内容塞进候选元数据（authority.md Investigate 义务）。
_SLICED_MODES_REQUIRING_KEY_INDEX = {
    SLICE_MODE_FIELD,
    SLICE_MODE_YAML_MAPPING_FIELD,
    SLICE_MODE_YAML_LIST_CHUNK,
}


@dataclass(frozen=True)
class ToolImplementationRef:
    tool_id: str
    module_path: str
    factory: str
    module_ref: LogicalPathRef | None = None


@dataclass(frozen=True)
class InvestigationArtifactRef:
    location: LogicalPathRef
    purpose: str


@dataclass
class ToolRequirement:
    tool_id: str
    description: str
    applicable_scenario: str
    parameters: Dict[str, Any]
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    implementation: Optional[ToolImplementationRef] = None
    implementation_gap: str = ""


@dataclass
class InvestigationManifest:
    schema_version: int
    project_id: str
    role: str
    source_revision: str
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    tool_requirements: list[ToolRequirement] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    artifact_refs: list[InvestigationArtifactRef] = field(default_factory=list)
    key_indexes: list[InvestigationKeyIndex] = field(default_factory=list)
    unresolved_reason: str = ""

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InvestigationManifest":
        evidence_refs = [_evidence_ref(item) for item in value.get("evidence_refs") or []]
        requirements = [_tool_requirement(item) for item in value.get("tool_requirements") or []]
        artifact_refs = []
        for item in value.get("artifact_refs") or []:
            if not isinstance(item, Mapping):
                raise TypeError("artifact_refs items must be objects")
            location = item.get("location")
            if not isinstance(location, Mapping):
                raise TypeError("InvestigationArtifactRef.location must be a LogicalPathRef object")
            artifact_refs.append(InvestigationArtifactRef(
                location=LogicalPathRef.from_mapping(location, field_path="artifact_refs.location"),
                purpose=str(item.get("purpose") or ""),
            ))
        raw_key_indexes = value.get("key_indexes") or []
        if not isinstance(raw_key_indexes, list):
            raise TypeError("InvestigationManifest.key_indexes must be a list")
        return cls(
            schema_version=int(value.get("schema_version") or 0),
            project_id=str(value.get("project_id") or ""),
            role=str(value.get("role") or ""),
            source_revision=str(value.get("source_revision") or ""),
            evidence_refs=evidence_refs,
            tool_requirements=requirements,
            artifacts={str(key): str(item) for key, item in dict(value.get("artifacts") or {}).items()},
            artifact_refs=artifact_refs,
            key_indexes=[InvestigationKeyIndex.from_dict(item) for item in raw_key_indexes],
            unresolved_reason=str(value.get("unresolved_reason") or ""),
        )

    def as_dict(self) -> Dict[str, Any]:
        data = to_dict(self)
        data["evidence_refs"] = [_evidence_dict(item) for item in self.evidence_refs]
        data["tool_requirements"] = [_tool_requirement_dict(item) for item in self.tool_requirements]
        data["artifact_refs"] = [
            {"location": dict(item.location.to_mapping()), "purpose": item.purpose}
            for item in self.artifact_refs
        ]
        data["key_indexes"] = [item.as_dict() for item in self.key_indexes]
        if self.schema_version >= 2:
            data.pop("artifacts", None)
        else:
            data.pop("artifact_refs", None)
        return data


def load_investigation_manifest(path: Path) -> InvestigationManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError("investigation manifest must be a JSON object")
    return InvestigationManifest.from_dict(raw)


def dump_investigation_manifest(manifest: InvestigationManifest, path: Path) -> None:
    if manifest.schema_version >= 2:
        repository_root = project_artifact_repository_root(Path(path))
        if repository_root is not None:
            write_active_artifact(
                "investigation_manifest",
                Path(path),
                manifest.as_dict(),
                repository_root=repository_root,
            )
        else:
            write_portable_export(Path(path), manifest.as_dict())
        return
    target = Path(path)
    if _is_registered_active_manifest_path(target):
        raise ValueError(
            "legacy Investigation schema v1 cannot be written to an active project package"
        )
    write_portable_export(target, manifest.as_dict())


def _is_registered_active_manifest_path(path: Path) -> bool:
    parts = path.resolve(strict=False).parts
    for index in range(len(parts) - 5):
        if (
            parts[index : index + 2] == ("impl", "projects")
            and parts[index + 3 : index + 5] == ("draft", "investigation")
            and parts[-1] == "manifest.json"
        ):
            return True
    return False


def validate_investigation_manifest(manifest: InvestigationManifest) -> None:
    if manifest.schema_version not in SUPPORTED_INVESTIGATION_SCHEMA_VERSIONS:
        raise ValueError(
            f"unsupported investigation schema_version={manifest.schema_version}; "
            f"expected one of {sorted(SUPPORTED_INVESTIGATION_SCHEMA_VERSIONS)}"
        )
    for field_name in ("project_id", "role", "source_revision"):
        if not str(getattr(manifest, field_name) or "").strip():
            raise ValueError(f"InvestigationManifest.{field_name} is required")

    evidence_ids: set[str] = set()
    for evidence in manifest.evidence_refs:
        _validate_evidence_ref(evidence)
        if evidence.ref_id in evidence_ids:
            raise ValueError(f"duplicate EvidenceRef.ref_id: {evidence.ref_id}")
        evidence_ids.add(evidence.ref_id)
    _validate_sliced_evidence_key_index_support(manifest)

    tool_ids: set[str] = set()
    for requirement in manifest.tool_requirements:
        _validate_tool_requirement(requirement)
        if requirement.tool_id in tool_ids:
            raise ValueError(f"duplicate ToolRequirement.tool_id: {requirement.tool_id}")
        tool_ids.add(requirement.tool_id)
        for evidence in requirement.evidence_refs:
            if evidence.ref_id in evidence_ids:
                raise ValueError(f"duplicate EvidenceRef.ref_id: {evidence.ref_id}")
            evidence_ids.add(evidence.ref_id)

    for artifact_path, purpose in manifest.artifacts.items():
        if not artifact_path.strip() or not purpose.strip():
            raise ValueError("InvestigationManifest.artifacts requires non-empty path and purpose")
    for artifact in manifest.artifact_refs:
        if not artifact.purpose.strip():
            raise ValueError("InvestigationArtifactRef.purpose is required")
    validate_investigation_key_indexes(manifest.key_indexes)
    if manifest.schema_version >= 2:
        for evidence in _manifest_evidence(manifest):
            if evidence.kind in {
                "source", "document", "trace", "replay", "test", "function",
                "code_reference", "dataset_reference",
            } and evidence.location_ref is None:
                raise ValueError(f"EvidenceRef requires LogicalPathRef in schema v2: {evidence.ref_id}")
        for requirement in manifest.tool_requirements:
            if requirement.implementation is not None and requirement.implementation.module_ref is None:
                raise ValueError(f"ToolImplementationRef requires module_ref in schema v2: {requirement.tool_id}")
        if manifest.artifacts:
            raise ValueError("InvestigationManifest schema v2 forbids legacy artifacts mapping")


def _validate_sliced_evidence_key_index_support(manifest: InvestigationManifest) -> None:
    """门禁：大切片资料必须有 key-index 支撑（CG-ENG-006 / P4）。

    调查层必须显式提供检索支撑：
    - manifest.key_indexes 中存在 collection_ref 匹配该 evidence_ref 的索引；
    - 字段级切片（field / yaml_mapping_field）可改用 EvidenceRef.metadata.key_index
      声明（字段枚举来自业务源、运行时才知道最新字段，由运行时从已物化切片确定
      性投影为 authority.evidence.<ref_id> 索引）；
    - 块级切片（yaml_list_chunk）的 chunk 边界由 slice 声明固定，调查层可直接登记
      manifest 索引；运行时投影只支持字段级，不接受声明绕过。
    core 不做隐式决策：没有声明的切片资料不投影索引，也不允许无支撑通过。
    """
    indexed_collections = {
        str(index.collection_ref or "").strip()
        for index in manifest.key_indexes
    }
    for evidence in _manifest_evidence(manifest):
        metadata = evidence.metadata or {}
        slice_spec = metadata.get("slice")
        if not isinstance(slice_spec, Mapping):
            continue
        mode = str(slice_spec.get("mode") or "").strip()
        if mode not in _SLICED_MODES_REQUIRING_KEY_INDEX:
            continue
        ref_id = str(evidence.ref_id or "").strip()
        if ref_id in indexed_collections:
            continue
        if mode != "yaml_list_chunk" and metadata.get("key_index"):
            continue
        raise ValueError(
            "sliced EvidenceRef requires key-index support "
            "(manifest key_indexes with matching collection_ref or "
            f"metadata.key_index declaration): {evidence.ref_id} (slice mode={mode})"
        )


def _evidence_ref(value: Any) -> EvidenceRef:
    if isinstance(value, EvidenceRef):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("evidence_refs items must be objects")
    raw_location = value.get("location")
    location_ref = (
        LogicalPathRef.from_mapping(raw_location, field_path=f"evidence_refs.{value.get('ref_id')}.location")
        if isinstance(raw_location, Mapping)
        else None
    )
    return EvidenceRef(
        ref_id=str(value.get("ref_id") or ""),
        source=str(value.get("source") or ""),
        kind=str(value.get("kind") or ""),
        stage=str(value.get("stage") or ""),
        summary=str(value.get("summary") or ""),
        location=str(raw_location or "") if location_ref is None else "",
        location_ref=location_ref,
        payload=value.get("payload"),
        metadata=dict(value.get("metadata") or {}),
    )


def _tool_requirement(value: Any) -> ToolRequirement:
    if isinstance(value, ToolRequirement):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("tool_requirements items must be objects")
    implementation = value.get("implementation")
    implementation_ref = None
    if implementation is not None:
        if not isinstance(implementation, Mapping):
            raise TypeError("ToolRequirement.implementation must be an object or null")
        raw_module = implementation.get("module_ref")
        implementation_ref = ToolImplementationRef(
            tool_id=str(implementation.get("tool_id") or ""),
            module_path=str(implementation.get("module_path") or ""),
            factory=str(implementation.get("factory") or ""),
            module_ref=(
                LogicalPathRef.from_mapping(raw_module, field_path="ToolImplementationRef.module_ref")
                if isinstance(raw_module, Mapping)
                else None
            ),
        )
    return ToolRequirement(
        tool_id=str(value.get("tool_id") or ""),
        description=str(value.get("description") or ""),
        applicable_scenario=str(value.get("applicable_scenario") or ""),
        parameters=dict(value.get("parameters") or {}),
        evidence_refs=[_evidence_ref(item) for item in value.get("evidence_refs") or []],
        implementation=implementation_ref,
        implementation_gap=str(value.get("implementation_gap") or ""),
    )


def _validate_evidence_ref(evidence: EvidenceRef) -> None:
    if not evidence.ref_id.strip():
        raise ValueError("EvidenceRef.ref_id is required")
    if not evidence.kind.strip():
        raise ValueError(f"EvidenceRef.kind is required: {evidence.ref_id}")
    if evidence.location_ref is None and not evidence.location.strip() and evidence.payload in (None, "", [], {}):
        raise ValueError(f"EvidenceRef requires location or payload: {evidence.ref_id}")
    if evidence.payload is not None:
        try:
            encoded = json.dumps(evidence.payload, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"EvidenceRef.payload must be JSON serializable: {evidence.ref_id}") from exc
        if len(encoded) > MAX_INLINE_EVIDENCE_PAYLOAD_BYTES:
            raise ValueError(
                f"EvidenceRef.payload exceeds {MAX_INLINE_EVIDENCE_PAYLOAD_BYTES} bytes: {evidence.ref_id}"
            )


def _validate_tool_requirement(requirement: ToolRequirement) -> None:
    for field_name in ("tool_id", "description", "applicable_scenario"):
        if not str(getattr(requirement, field_name) or "").strip():
            raise ValueError(f"ToolRequirement.{field_name} is required")
    if requirement.parameters.get("type") != "object":
        raise ValueError(f"ToolRequirement.parameters.type must be object: {requirement.tool_id}")
    for evidence in requirement.evidence_refs:
        _validate_evidence_ref(evidence)
    if requirement.implementation is None:
        if not requirement.implementation_gap.strip():
            raise ValueError(
                f"ToolRequirement without implementation requires implementation_gap: {requirement.tool_id}"
            )
        return
    implementation = requirement.implementation
    if implementation.tool_id != requirement.tool_id:
        raise ValueError(f"ToolImplementationRef.tool_id mismatch: {requirement.tool_id}")
    if not implementation.module_path.strip() or not implementation.factory.strip():
        if implementation.module_ref is None or not implementation.factory.strip():
            raise ValueError(f"ToolImplementationRef module reference/factory are required: {requirement.tool_id}")
    if requirement.implementation_gap.strip():
        raise ValueError(
            f"implemented ToolRequirement cannot also declare implementation_gap: {requirement.tool_id}"
        )


def _evidence_dict(value: EvidenceRef) -> Dict[str, Any]:
    data = to_dict(value)
    data.pop("location_ref", None)
    if value.location_ref is not None:
        data["location"] = dict(value.location_ref.to_mapping())
    return data


def _tool_requirement_dict(value: ToolRequirement) -> Dict[str, Any]:
    data = to_dict(value)
    data["evidence_refs"] = [_evidence_dict(item) for item in value.evidence_refs]
    if value.implementation is not None:
        implementation = {
            "tool_id": value.implementation.tool_id,
            "factory": value.implementation.factory,
        }
        if value.implementation.module_ref is not None:
            implementation["module_ref"] = dict(value.implementation.module_ref.to_mapping())
        else:
            implementation["module_path"] = value.implementation.module_path
        data["implementation"] = implementation
    return data


def _manifest_evidence(manifest: InvestigationManifest):
    yield from manifest.evidence_refs
    for requirement in manifest.tool_requirements:
        yield from requirement.evidence_refs
