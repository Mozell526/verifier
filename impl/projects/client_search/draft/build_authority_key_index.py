"""Deterministically rebuild Authority investigation navigation indexes.

The collection index projects only investigated MaterialDecision metadata.  It
must not embed arbitrary first-N samples from large source materials.  Large
materials may provide a separate internal index whose ``search_text`` is a
source-derived projection and whose targets navigate back to the original
EvidenceRef.  No AI-authored synonym or case answer is accepted here.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import yaml

from impl.core.authority_key_index import build_material_decision_key_index
from impl.core.project_loader import load_project, resolve_role_assets
from impl.core.schema.investigation_judge import load_authority_investigation_report
from impl.core.schema.investigation import InvestigationManifest, dump_investigation_manifest

MATERIAL_INDEX_KEY = "authority.material-decisions"
PLANFULLNAME_INDEX_KEY = "material.business-planfullname-enums.values"
REPORT_RELATIVE = "docs/authority-investigation-report.json"
MANIFEST_RELATIVE = "manifest.json"
_PLANFULLNAME_CHUNK_SIZE = 100


def _investigation_root(spec) -> Path:
    selected = [
        item
        for item in resolve_role_assets(spec, "judge", use_candidate=True)
        if item["mapping"].kind == "investigation"
    ]
    if len(selected) != 1:
        raise RuntimeError(f"expected exactly one judge investigation package, got {len(selected)}")
    return Path(selected[0]["path"])


def _material_entries(report) -> list[dict[str, str]]:
    """复用 Core 单一来源：material decisions + coverage-gap 条目同构。"""
    return [
        entry.as_dict()
        for entry in build_material_decision_key_index(report).entries
    ]


def _planfullname_entries(spec) -> list[dict[str, str]]:
    path = Path(spec.source_path("planfullname_enums"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = data["polNoInfo.plancodeinfo.planfullname"]["values"]
    entries = []
    for offset in range(0, len(values), _PLANFULLNAME_CHUNK_SIZE):
        chunk = [str(value) for value in values[offset : offset + _PLANFULLNAME_CHUNK_SIZE]]
        end = offset + len(chunk) - 1
        locator = f"polNoInfo.plancodeinfo.planfullname.values[{offset}:{end}]"
        entries.append(
            {
                "key": f"values-{offset:04d}-{end:04d}",
                "name": f"产品全称合法值 {offset + 1}-{end + 1}",
                "search_text": " ".join(chunk),
                "target_ref": (
                    "evidence-navigation://business-planfullname-enums/"
                    + quote(locator, safe="")
                ),
            }
        )
    return entries


def build_indexes(spec) -> list[dict[str, object]]:
    root = _investigation_root(spec)
    report = load_authority_investigation_report(root / REPORT_RELATIVE)
    return [
        {
            "index_key": MATERIAL_INDEX_KEY,
            "collection_ref": "authority-investigation-report",
            "target_kind": "material_decision",
            "entry_granularity": "investigated_statement",
            "entries": _material_entries(report),
        },
        {
            "index_key": PLANFULLNAME_INDEX_KEY,
            "collection_ref": "business-planfullname-enums",
            "target_kind": "evidence_locator",
            "entry_granularity": "yaml_list_range",
            "entries": _planfullname_entries(spec),
        },
    ]


def main() -> None:
    spec = load_project("client_search")
    indexes = build_indexes(spec)
    manifest_path = _investigation_root(spec) / MANIFEST_RELATIVE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["key_indexes"] = indexes
    dump_investigation_manifest(
        InvestigationManifest.from_dict(manifest), manifest_path
    )
    for index in indexes:
        print(f"{index['index_key']}: entries={len(index['entries'])}")


if __name__ == "__main__":
    main()
