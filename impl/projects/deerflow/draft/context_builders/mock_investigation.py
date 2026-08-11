from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from impl.core.context.models import ContextUnitRecord


def build_context_unit_records(
    spec: Any,
    role: str,
    use_candidate: bool,
    selected_assets: list[Mapping[str, Any]],
) -> list[ContextUnitRecord]:
    investigation = next(
        (
            item
            for item in selected_assets
            if item["mapping"].kind == "investigation"
            and item["mapping"].asset_id == "mock_investigation"
            and item["available"]
        ),
        None,
    )
    if investigation is None:
        raise FileNotFoundError("candidate DeerFlow Mock requires mock_investigation")

    contract = (
        Path(investigation["path"])
        / "docs"
        / "mock-investigation-contract.json"
    )
    if not contract.is_file():
        raise FileNotFoundError(
            f"DeerFlow Mock investigation contract is unavailable: {contract}"
        )
    return [
        ContextUnitRecord(
            id="project.deerflow.mock.investigation.contract",
            name="DeerFlow Mock investigation contract",
            description=(
                "Business values, evaluation dimensions, demand spaces and hard "
                "user-knowledge boundaries for candidate Mock generation."
            ),
            content=None,
            content_ref=contract.resolve().as_uri(),
            project_id=spec.project_id,
            scope="project_static",
            roles=(role,),
            unit_type="mock_investigation_contract",
            source_type="investigation_context_builder",
            tags={
                "mode": "draft" if use_candidate else "production",
                "asset_id": investigation["mapping"].asset_id,
                "source": investigation["source"],
            },
        )
    ]
