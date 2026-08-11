from __future__ import annotations

import hashlib
import json
from pathlib import Path

from impl.core.investigation import validate_investigation_package
from impl.core.path_contract import LogicalPathRef, PathScope
from impl.core.schema import (
    EvidenceRef,
    InvestigationArtifactRef,
    InvestigationManifest,
    dump_investigation_manifest,
    load_investigation_manifest,
)


def test_v2_manifest_round_trips_and_resolves_logical_paths(tmp_path: Path) -> None:
    project = tmp_path / "repo" / "impl" / "projects" / "demo"
    package = project / "draft" / "investigation" / "attribute"
    business = tmp_path / "business"
    package.mkdir(parents=True)
    business.mkdir()
    source = business / "src" / "api.py"
    source.parent.mkdir()
    source.write_text("def create_app():\n    pass\n", encoding="utf-8")
    overview = package / "overview.md"
    overview.write_text("# overview\n", encoding="utf-8")
    manifest = InvestigationManifest(
        schema_version=2,
        project_id="demo",
        role="attribute",
        source_revision="revision-1",
        evidence_refs=[
            EvidenceRef(
                ref_id="business-api",
                source="business",
                kind="function",
                location_ref=LogicalPathRef(
                    PathScope.BUSINESS_SOURCE,
                    "src/api.py",
                    symbol="create_app",
                    revision="revision-1",
                    sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                ),
                metadata={
                    "source_revision": "revision-1",
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                },
            )
        ],
        artifact_refs=[
            InvestigationArtifactRef(
                LogicalPathRef(PathScope.ARTIFACT_PACKAGE, "overview.md"),
                "overview",
            )
        ],
    )
    manifest_path = package / "manifest.json"

    dump_investigation_manifest(manifest, manifest_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert raw["evidence_refs"][0]["location"]["location_scope"] == "business_source"
    assert "/Users/" not in manifest_path.read_text(encoding="utf-8")
    loaded = load_investigation_manifest(manifest_path)
    result = validate_investigation_package(
        package,
        project_root=project,
        expected_project_id="demo",
        expected_role="attribute",
        source_root=business,
        expected_source_revision="revision-1",
    )
    assert loaded.evidence_refs[0].location_ref is not None
    assert result["evidence_files"] == [str(source.resolve())]
