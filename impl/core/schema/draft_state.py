from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..path_contract import LogicalPathRef, PathContractError, PathScope


DRAFT_LOOP_STATE_VERSION = 2
DRAFT_RUN_REPORT_VERSION = 2


@dataclass(frozen=True)
class DraftEvidencePointer:
    artifact: LogicalPathRef
    pointer: str = ""

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        field_path: str,
    ) -> "DraftEvidencePointer":
        unknown = sorted(set(value) - {"artifact", "pointer"})
        if unknown:
            raise PathContractError(
                "PATH_TYPE_MISMATCH", field_path, f"unknown field {unknown[0]!r}"
            )
        artifact = value.get("artifact")
        if not isinstance(artifact, Mapping):
            raise PathContractError(
                "PATH_TYPE_MISMATCH", field_path, "artifact must be a LogicalPathRef"
            )
        pointer = value.get("pointer", "")
        if not isinstance(pointer, str) or (pointer and not pointer.startswith("#")):
            raise PathContractError(
                "PATH_TYPE_MISMATCH",
                field_path,
                "pointer must be empty or start with '#'",
            )
        return cls(
            LogicalPathRef.from_mapping(artifact, field_path=f"{field_path}.artifact"),
            pointer,
        )

    def to_mapping(self) -> dict[str, Any]:
        value: dict[str, Any] = {"artifact": dict(self.artifact.to_mapping())}
        if self.pointer:
            value["pointer"] = self.pointer
        return value


@dataclass
class DraftLoopIteration:
    iteration: int
    run_report: LogicalPathRef
    draft_fingerprint: str
    decision: str = ""
    route: str = ""
    reason: str = ""
    evidence: list[DraftEvidencePointer] = field(default_factory=list)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        field_path: str,
    ) -> "DraftLoopIteration":
        allowed = {
            "iteration",
            "run_report",
            "draft_fingerprint",
            "decision",
            "route",
            "reason",
            "evidence",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise PathContractError(
                "PATH_TYPE_MISMATCH", field_path, f"unknown field {unknown[0]!r}"
            )
        raw_report = value.get("run_report")
        if not isinstance(raw_report, Mapping):
            raise PathContractError(
                "PATH_SCHEMA_BYPASS",
                f"{field_path}.run_report",
                "run_report must be a LogicalPathRef",
            )
        raw_evidence = value.get("evidence") or []
        if not isinstance(raw_evidence, list):
            raise PathContractError(
                "PATH_TYPE_MISMATCH", f"{field_path}.evidence", "expected a list"
            )
        evidence: list[DraftEvidencePointer] = []
        for index, item in enumerate(raw_evidence):
            if not isinstance(item, Mapping):
                raise PathContractError(
                    "PATH_SCHEMA_BYPASS",
                    f"{field_path}.evidence[{index}]",
                    "evidence pointers must use the structured artifact schema",
                )
            evidence.append(
                DraftEvidencePointer.from_mapping(
                    item, field_path=f"{field_path}.evidence[{index}]"
                )
            )
        return cls(
            iteration=int(value.get("iteration") or 0),
            run_report=LogicalPathRef.from_mapping(
                raw_report, field_path=f"{field_path}.run_report"
            ),
            draft_fingerprint=str(value.get("draft_fingerprint") or ""),
            decision=str(value.get("decision") or ""),
            route=str(value.get("route") or ""),
            reason=str(value.get("reason") or ""),
            evidence=evidence,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "run_report": dict(self.run_report.to_mapping()),
            "draft_fingerprint": self.draft_fingerprint,
            "decision": self.decision,
            "route": self.route,
            "reason": self.reason,
            "evidence": [item.to_mapping() for item in self.evidence],
        }


@dataclass
class DraftLoopState:
    schema_version: int
    project_id: str
    role: str
    objective: str
    review: str
    max_iterations: int
    cases_sha256: str
    frozen_current_sha256: str
    source_revision: str
    status: str = "active"
    iterations: list[DraftLoopIteration] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DraftLoopState":
        allowed = {
            "schema_version",
            "project_id",
            "role",
            "objective",
            "review",
            "max_iterations",
            "cases_sha256",
            "frozen_current_sha256",
            "source_revision",
            "status",
            "iterations",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise PathContractError(
                "PATH_TYPE_MISMATCH", "draft_loop", f"unknown field {unknown[0]!r}"
            )
        version = int(value.get("schema_version") or 0)
        if version != DRAFT_LOOP_STATE_VERSION:
            raise PathContractError(
                "PATH_SCHEMA_BYPASS",
                "draft_loop.schema_version",
                f"expected portable Draft Loop schema v{DRAFT_LOOP_STATE_VERSION}",
            )
        raw_iterations = value.get("iterations") or []
        if not isinstance(raw_iterations, list):
            raise PathContractError(
                "PATH_TYPE_MISMATCH", "draft_loop.iterations", "expected a list"
            )
        iterations: list[DraftLoopIteration] = []
        for index, item in enumerate(raw_iterations):
            if not isinstance(item, Mapping):
                raise PathContractError(
                    "PATH_TYPE_MISMATCH",
                    f"draft_loop.iterations[{index}]",
                    "iteration must be an object",
                )
            iteration = DraftLoopIteration.from_mapping(
                item, field_path=f"iterations[{index}]"
            )
            if iteration.iteration != index + 1:
                raise PathContractError(
                    "PATH_TYPE_MISMATCH",
                    f"iterations[{index}].iteration",
                    "iteration numbers must be contiguous and one-based",
                )
            if iteration.run_report.location_scope is not PathScope.PROJECT_PACKAGE:
                raise PathContractError(
                    "PATH_PREFIX_NOT_ALLOWED",
                    f"iterations[{index}].run_report",
                    "Draft run reports must use project_package scope",
                )
            if not iteration.run_report.sha256:
                raise PathContractError(
                    "PATH_TYPE_MISMATCH",
                    f"iterations[{index}].run_report.sha256",
                    "active Draft run reports require a content hash",
                )
            iterations.append(iteration)
        return cls(
            schema_version=version,
            project_id=str(value.get("project_id") or ""),
            role=str(value.get("role") or ""),
            objective=str(value.get("objective") or ""),
            review=str(value.get("review") or ""),
            max_iterations=int(value.get("max_iterations") or 0),
            cases_sha256=str(value.get("cases_sha256") or ""),
            frozen_current_sha256=str(value.get("frozen_current_sha256") or ""),
            source_revision=str(value.get("source_revision") or ""),
            status=str(value.get("status") or "active"),
            iterations=iterations,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "role": self.role,
            "objective": self.objective,
            "review": self.review,
            "max_iterations": self.max_iterations,
            "cases_sha256": self.cases_sha256,
            "frozen_current_sha256": self.frozen_current_sha256,
            "source_revision": self.source_revision,
            "status": self.status,
            "iterations": [item.to_mapping() for item in self.iterations],
        }
