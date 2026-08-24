"""Strict JSON schema for the Mock investigation hand-off contract."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from ..portable_artifact import (
    project_artifact_repository_root,
    write_active_artifact,
    write_portable_export,
)


MOCK_CONTRACT_SCHEMA_VERSION = 1
_ROOT_FIELDS = {"schema_version", "business_values", "evaluation_scope", "demand_spaces"}
_VALUE_FIELDS = {
    "value_id",
    "beneficiary",
    "business_need",
    "system_contribution",
    "desired_outcome",
    "evidence_ref_ids",
}
_SCOPE_FIELDS = {"dimensions"}
_DIMENSION_FIELDS = {
    "dimension_id",
    "name",
    "definition",
    "judgment_question",
    "evidence_ref_ids",
}
_SPACE_FIELDS = {
    "space_id",
    "name",
    "business_value_ids",
    "demand_definition",
    "evaluation_coverage",
    "variation_space",
    "validity_constraints",
    "evidence_ref_ids",
}
_COVERAGE_FIELDS = {"dimension_id", "mock_data_requirement"}
_RESERVED_CONTENT = re.compile(
    r"(?i)(?:\bcase[_ -]?id\b|\bunseen[_ -]?case\b|\bexpected[_ -]?answer\b|"
    r"\bcurrent[_ -]?verdict\b|\bcandidate[_ -]?instruction\b|\bjudge_result\b)"
)


@dataclass(frozen=True)
class BusinessValue:
    value_id: str
    beneficiary: str
    business_need: str
    system_contribution: str
    desired_outcome: str
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationDimension:
    dimension_id: str
    name: str
    definition: str
    judgment_question: str
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationScope:
    dimensions: tuple[EvaluationDimension, ...]


@dataclass(frozen=True)
class EvaluationDimensionCoverage:
    dimension_id: str
    mock_data_requirement: str


@dataclass(frozen=True)
class MockDemandSpace:
    space_id: str
    name: str
    business_value_ids: tuple[str, ...]
    demand_definition: str
    evaluation_coverage: tuple[EvaluationDimensionCoverage, ...]
    variation_space: tuple[str, ...]
    validity_constraints: tuple[str, ...]
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class MockInvestigationContract:
    business_values: tuple[BusinessValue, ...]
    evaluation_scope: EvaluationScope
    demand_spaces: tuple[MockDemandSpace, ...]
    schema_version: int = MOCK_CONTRACT_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MockInvestigationContract":
        root = _object(value, "MockInvestigationContract", _ROOT_FIELDS)
        schema_version = _required_int(root, "schema_version", "MockInvestigationContract")
        values = tuple(
            _business_value(item, index)
            for index, item in enumerate(
                _required_list(root, "business_values", "MockInvestigationContract")
            )
        )
        scope_raw = _object(
            _required(root, "evaluation_scope", "MockInvestigationContract"),
            "evaluation_scope",
            _SCOPE_FIELDS,
        )
        dimensions = tuple(
            _evaluation_dimension(item, index)
            for index, item in enumerate(_required_list(scope_raw, "dimensions", "evaluation_scope"))
        )
        spaces = tuple(
            _demand_space(item, index)
            for index, item in enumerate(
                _required_list(root, "demand_spaces", "MockInvestigationContract")
            )
        )
        return cls(values, EvaluationScope(dimensions), spaces, schema_version)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "business_values": [
                {
                    "value_id": item.value_id,
                    "beneficiary": item.beneficiary,
                    "business_need": item.business_need,
                    "system_contribution": item.system_contribution,
                    "desired_outcome": item.desired_outcome,
                    "evidence_ref_ids": list(item.evidence_ref_ids),
                }
                for item in self.business_values
            ],
            "evaluation_scope": {
                "dimensions": [
                    {
                        "dimension_id": item.dimension_id,
                        "name": item.name,
                        "definition": item.definition,
                        "judgment_question": item.judgment_question,
                        "evidence_ref_ids": list(item.evidence_ref_ids),
                    }
                    for item in self.evaluation_scope.dimensions
                ]
            },
            "demand_spaces": [
                {
                    "space_id": item.space_id,
                    "name": item.name,
                    "business_value_ids": list(item.business_value_ids),
                    "demand_definition": item.demand_definition,
                    "evaluation_coverage": [
                        {
                            "dimension_id": coverage.dimension_id,
                            "mock_data_requirement": coverage.mock_data_requirement,
                        }
                        for coverage in item.evaluation_coverage
                    ],
                    "variation_space": list(item.variation_space),
                    "validity_constraints": list(item.validity_constraints),
                    "evidence_ref_ids": list(item.evidence_ref_ids),
                }
                for item in self.demand_spaces
            ],
        }


def load_mock_contract(path: Path) -> MockInvestigationContract:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return MockInvestigationContract.from_dict(raw)


def dump_mock_contract(contract: MockInvestigationContract, path: Path) -> None:
    target = Path(path)
    repository_root = project_artifact_repository_root(target)
    if repository_root is None:
        write_portable_export(target, contract.as_dict())
        return
    write_active_artifact(
        "mock_investigation_contract",
        target,
        contract.as_dict(),
        repository_root=repository_root,
    )


def validate_mock_contract(
    contract: MockInvestigationContract,
    *,
    evidence_ref_ids: Optional[set[str]] = None,
) -> None:
    if contract.schema_version != MOCK_CONTRACT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported MockInvestigationContract.schema_version: {contract.schema_version}"
        )
    if not contract.business_values:
        raise ValueError("MockInvestigationContract.business_values must be non-empty")

    value_ids: set[str] = set()
    for value in contract.business_values:
        _unique_required_id(value.value_id, value_ids, "BusinessValue.value_id")
        for field_name in ("beneficiary", "business_need", "system_contribution", "desired_outcome"):
            text = _required_text(
                getattr(value, field_name), f"BusinessValue.{field_name}: {value.value_id}"
            )
            _reject_reserved(text, f"BusinessValue.{field_name}")
        _require_nonempty_texts(value.evidence_ref_ids, f"BusinessValue.evidence_ref_ids: {value.value_id}")
        _check_evidence_refs(value.evidence_ref_ids, evidence_ref_ids, f"BusinessValue {value.value_id}")

    dimensions = contract.evaluation_scope.dimensions
    if not dimensions:
        raise ValueError("EvaluationScope.dimensions must be non-empty")
    dimension_ids: set[str] = set()
    for dimension in dimensions:
        _unique_required_id(dimension.dimension_id, dimension_ids, "EvaluationDimension.dimension_id")
        for field_name in ("name", "definition", "judgment_question"):
            text = _required_text(
                getattr(dimension, field_name),
                f"EvaluationDimension.{field_name}: {dimension.dimension_id}",
            )
            _reject_reserved(text, f"EvaluationDimension.{field_name}")
        _require_nonempty_texts(
            dimension.evidence_ref_ids,
            f"EvaluationDimension.evidence_ref_ids: {dimension.dimension_id}",
        )
        _check_evidence_refs(
            dimension.evidence_ref_ids,
            evidence_ref_ids,
            f"EvaluationDimension {dimension.dimension_id}",
        )

    if not contract.demand_spaces:
        raise ValueError("MockInvestigationContract.demand_spaces must be non-empty")
    space_ids: set[str] = set()
    covered_values: set[str] = set()
    covered_dimensions: set[str] = set()
    for space in contract.demand_spaces:
        _unique_required_id(space.space_id, space_ids, "MockDemandSpace.space_id")
        _required_text(space.name, f"MockDemandSpace.name: {space.space_id}")
        _reject_reserved(
            _required_text(space.demand_definition, f"MockDemandSpace.demand_definition: {space.space_id}"),
            "MockDemandSpace.demand_definition",
        )
        _require_nonempty_texts(
            space.business_value_ids, f"MockDemandSpace.business_value_ids: {space.space_id}"
        )
        if len(set(space.business_value_ids)) != len(space.business_value_ids):
            raise ValueError(f"MockDemandSpace has duplicate business_value_ids: {space.space_id}")
        unknown_values = sorted(set(space.business_value_ids) - value_ids)
        if unknown_values:
            raise ValueError(
                f"MockDemandSpace {space.space_id} references unknown business value_id: "
                + ", ".join(unknown_values)
            )
        covered_values.update(space.business_value_ids)
        if not space.evaluation_coverage:
            raise ValueError(
                f"MockDemandSpace must cover at least one evaluation dimension: {space.space_id}"
            )
        coverage_ids: set[str] = set()
        for coverage in space.evaluation_coverage:
            _required_text(
                coverage.dimension_id,
                f"EvaluationDimensionCoverage.dimension_id: {space.space_id}",
            )
            if coverage.dimension_id in coverage_ids:
                raise ValueError(
                    f"MockDemandSpace has duplicate evaluation coverage: {space.space_id}/"
                    f"{coverage.dimension_id}"
                )
            coverage_ids.add(coverage.dimension_id)
            if coverage.dimension_id not in dimension_ids:
                raise ValueError(
                    f"MockDemandSpace {space.space_id} evaluation_coverage references unknown "
                    f"dimension_id: {coverage.dimension_id}"
                )
            _reject_reserved(
                _required_text(
                    coverage.mock_data_requirement,
                    f"EvaluationDimensionCoverage.mock_data_requirement: "
                    f"{space.space_id}/{coverage.dimension_id}",
                ),
                "EvaluationDimensionCoverage.mock_data_requirement",
            )
            covered_dimensions.add(coverage.dimension_id)
        _require_nonempty_texts(space.variation_space, f"MockDemandSpace.variation_space: {space.space_id}")
        _require_nonempty_texts(
            space.validity_constraints, f"MockDemandSpace.validity_constraints: {space.space_id}"
        )
        for text in (*space.variation_space, *space.validity_constraints):
            _reject_reserved(text, f"MockDemandSpace {space.space_id}")
        _require_nonempty_texts(space.evidence_ref_ids, f"MockDemandSpace.evidence_ref_ids: {space.space_id}")
        _check_evidence_refs(space.evidence_ref_ids, evidence_ref_ids, f"MockDemandSpace {space.space_id}")

    uncovered_values = sorted(value_ids - covered_values)
    if uncovered_values:
        raise ValueError("business values not covered by any MockDemandSpace: " + ", ".join(uncovered_values))
    uncovered_dimensions = sorted(dimension_ids - covered_dimensions)
    if uncovered_dimensions:
        raise ValueError(
            "evaluation dimensions not covered by any MockDemandSpace: "
            + ", ".join(uncovered_dimensions)
        )


def _business_value(value: Any, index: int) -> BusinessValue:
    owner = f"business_values[{index}]"
    item = _object(value, owner, _VALUE_FIELDS)
    return BusinessValue(
        _required_str(item, "value_id", owner),
        _required_str(item, "beneficiary", owner),
        _required_str(item, "business_need", owner),
        _required_str(item, "system_contribution", owner),
        _required_str(item, "desired_outcome", owner),
        _str_tuple(item, "evidence_ref_ids", owner),
    )


def _evaluation_dimension(value: Any, index: int) -> EvaluationDimension:
    owner = f"evaluation_scope.dimensions[{index}]"
    item = _object(value, owner, _DIMENSION_FIELDS)
    return EvaluationDimension(
        _required_str(item, "dimension_id", owner),
        _required_str(item, "name", owner),
        _required_str(item, "definition", owner),
        _required_str(item, "judgment_question", owner),
        _str_tuple(item, "evidence_ref_ids", owner),
    )


def _demand_space(value: Any, index: int) -> MockDemandSpace:
    owner = f"demand_spaces[{index}]"
    item = _object(value, owner, _SPACE_FIELDS)
    coverage = tuple(
        _coverage(coverage_item, owner, coverage_index)
        for coverage_index, coverage_item in enumerate(
            _required_list(item, "evaluation_coverage", owner)
        )
    )
    return MockDemandSpace(
        _required_str(item, "space_id", owner),
        _required_str(item, "name", owner),
        _str_tuple(item, "business_value_ids", owner),
        _required_str(item, "demand_definition", owner),
        coverage,
        _str_tuple(item, "variation_space", owner),
        _str_tuple(item, "validity_constraints", owner),
        _str_tuple(item, "evidence_ref_ids", owner),
    )


def _coverage(value: Any, owner: str, index: int) -> EvaluationDimensionCoverage:
    coverage_owner = f"{owner}.evaluation_coverage[{index}]"
    item = _object(value, coverage_owner, _COVERAGE_FIELDS)
    return EvaluationDimensionCoverage(
        _required_str(item, "dimension_id", coverage_owner),
        _required_str(item, "mock_data_requirement", coverage_owner),
    )


def _object(value: Any, owner: str, allowed: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{owner} must be a JSON object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{owner} contains unknown field: {unknown[0]}")
    return value


def _required(value: Mapping[str, Any], key: str, owner: str) -> Any:
    if key not in value:
        raise ValueError(f"{owner}.{key} is required")
    return value[key]


def _required_int(value: Mapping[str, Any], key: str, owner: str) -> int:
    raw = _required(value, key, owner)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise TypeError(f"{owner}.{key} must be an integer")
    return raw


def _required_str(value: Mapping[str, Any], key: str, owner: str) -> str:
    raw = _required(value, key, owner)
    if not isinstance(raw, str):
        raise TypeError(f"{owner}.{key} must be a string")
    return raw


def _required_list(value: Mapping[str, Any], key: str, owner: str) -> Sequence[Any]:
    raw = _required(value, key, owner)
    if not isinstance(raw, list):
        raise TypeError(f"{owner}.{key} must be a JSON array")
    return raw


def _str_tuple(value: Mapping[str, Any], key: str, owner: str) -> tuple[str, ...]:
    raw = _required_list(value, key, owner)
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise TypeError(f"{owner}.{key}[{index}] must be a string")
    return tuple(raw)


def _unique_required_id(value: str, seen: set[str], owner: str) -> None:
    _required_text(value, owner)
    if value in seen:
        raise ValueError(f"duplicate {owner}: {value}")
    seen.add(value)


def _required_text(value: str, owner: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} is required")
    return value.strip()


def _require_nonempty_texts(values: tuple[str, ...], owner: str) -> None:
    if not values:
        raise ValueError(f"{owner} must be non-empty")
    for index, value in enumerate(values):
        _required_text(value, f"{owner}[{index}]")


def _check_evidence_refs(
    refs: tuple[str, ...], known: Optional[set[str]], owner: str
) -> None:
    if known is None:
        return
    unknown = sorted(set(refs) - known)
    if unknown:
        raise ValueError(f"{owner} references unknown EvidenceRef.ref_id: " + ", ".join(unknown))


def _reject_reserved(text: str, owner: str) -> None:
    match = _RESERVED_CONTENT.search(text)
    if match:
        raise ValueError(f"{owner} contains forbidden case/answer/instruction content: {match.group(0)}")
