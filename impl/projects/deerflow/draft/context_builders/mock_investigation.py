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
        raise ValueError("candidate DeerFlow Mock context requires mock_investigation")

    contract = Path(investigation["path"]) / "docs" / "user-goal-and-scenario-contract.md"
    if not contract.is_file():
        raise FileNotFoundError(f"deerflow Mock business contract is unavailable: {contract}")
    return [
        ContextUnitRecord(
            id="project.deerflow.mock.business_contract",
            name="DeerFlow potential user population boundary",
            description="A broad user-population and hard knowledge-boundary contract for open-world Mock generation.",
            content=None,
            content_ref=contract.resolve().as_uri(),
            project_id=spec.project_id,
            scope="project_static",
            roles=(role,),
            unit_type="mock_business_contract",
            source_type="investigation_context_builder",
            tags={
                "mode": "draft" if use_candidate else "production",
                "asset_id": investigation["mapping"].asset_id,
                "source": investigation["source"],
            },
        )
    ]
