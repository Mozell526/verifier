"""Tests for the business-source staleness public facility.

Covers spec/grill/staleness_public_facility.md: slice-level detection,
consumption-mode routing, strict/warn boundary and affected-asset projection.
"""
from __future__ import annotations

import json

import pytest

from impl.core.source_staleness import (
    ROUTING_ABSORB,
    ROUTING_CLEAN,
    ROUTING_NEEDS_REVIEW,
    ROUTING_POSITIONAL_REBUILD,
    StalenessPolicyViolation,
    apply_staleness_policy,
    compute_slice_hashes,
    detect_ref_drift,
    file_sha256,
    normalize_consumption,
    slice_entries,
)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


_FIELD_YAML = """\
intents:
  - id: license_plate_no
    field: licensePlateNo
    is_supported: false
    retrieval_text: 车牌号
  - id: is_life_insured
    field: isLifeInsured
    is_supported: true
    retrieval_text: 投被保人
"""

_FIELD_SLICE_SPEC = {"mode": "field", "list_key": "intents", "field_key": "field"}

_CHUNK_YAML = """\
root:
  values:
    - 产品A
    - 产品B
    - 产品C
    - 产品D
"""

_CHUNK_SLICE_SPEC = {"mode": "yaml_list_chunk", "root_key": "root", "list_key": "values", "chunk_size": 2}


def test_slice_hashes_field_mode_are_key_stable(tmp_path):
    path = _write(tmp_path, "field_definitions_args.yaml", _FIELD_YAML)
    first = compute_slice_hashes(path, _FIELD_SLICE_SPEC)
    assert set(first) == {"field:licensePlateNo", "field:isLifeInsured"}
    # inserting an unrelated field must not change existing slice hashes
    grown = _write(
        tmp_path,
        "grown.yaml",
        _FIELD_YAML + "  - id: other\n    field: otherField\n    is_supported: true\n    retrieval_text: 其他\n",
    )
    second = compute_slice_hashes(grown, _FIELD_SLICE_SPEC)
    assert second["field:licensePlateNo"] == first["field:licensePlateNo"]
    assert second["field:isLifeInsured"] == first["field:isLifeInsured"]
    assert "field:otherField" in second


def test_slice_entries_chunk_mode_is_positional(tmp_path):
    path = _write(tmp_path, "enums.yaml", _CHUNK_YAML)
    entries = slice_entries(path, _CHUNK_SLICE_SPEC)
    assert [entry["slice_key"] for entry in entries] == ["chunk:1", "chunk:2"]


def test_detect_drift_clean_when_file_unchanged(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=path,
        declared_sha256=file_sha256(path),
        slice_spec=_FIELD_SLICE_SPEC,
        declared_slice_hashes=compute_slice_hashes(path, _FIELD_SLICE_SPEC),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
    )
    assert report.routing == ROUTING_CLEAN
    assert not report.file_changed


def test_detect_drift_localizes_changed_slice(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    frozen = compute_slice_hashes(path, _FIELD_SLICE_SPEC)
    changed = _write(
        tmp_path,
        "changed.yaml",
        _FIELD_YAML.replace("is_supported: false", "is_supported: true", 1),
    )
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
        slice_spec=_FIELD_SLICE_SPEC,
        declared_slice_hashes=frozen,
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
    )
    assert report.file_changed
    assert [change.slice_key for change in report.slice_changes] == ["field:licensePlateNo"]


def test_routing_absorb_for_key_live_without_decisions(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    changed = _write(tmp_path, "changed.yaml", _FIELD_YAML.replace("true", "false", 1))
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
        slice_spec=_FIELD_SLICE_SPEC,
        declared_slice_hashes=compute_slice_hashes(path, _FIELD_SLICE_SPEC),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
        navigation_entry_keys=["values-0000-0099"],
        embedding_entry_keys=["licensePlateNo"],
    )
    assert report.routing == ROUTING_ABSORB
    assert report.affected_embedding_entries == ["licensePlateNo"]


def test_routing_needs_review_when_decision_referenced_without_dep_keys(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    changed = _write(tmp_path, "changed.yaml", _FIELD_YAML.replace("true", "false", 1))
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
        slice_spec=_FIELD_SLICE_SPEC,
        declared_slice_hashes=compute_slice_hashes(path, _FIELD_SLICE_SPEC),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
        decisions=["business-field-definitions.decision-1"],
    )
    assert report.routing == ROUTING_NEEDS_REVIEW
    assert report.affected_decisions == ["business-field-definitions.decision-1"]


def test_routing_needs_review_only_for_dep_keyed_hits(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    # "true" -> "false" flips isLifeInsured (the second intent's slice).
    changed = _write(tmp_path, "changed.yaml", _FIELD_YAML.replace("true", "false", 1))
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
        slice_spec=_FIELD_SLICE_SPEC,
        declared_slice_hashes=compute_slice_hashes(path, _FIELD_SLICE_SPEC),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
        decisions=[
            "business-field-definitions.decision-1",
            "business-field-definitions.decision-2",
        ],
        dep_keyed_decisions=[
            "business-field-definitions.decision-1:field:licensePlateNo",
            "business-field-definitions.decision-2:field:isLifeInsured",
        ],
    )
    assert report.routing == ROUTING_NEEDS_REVIEW
    assert [change.slice_key for change in report.slice_changes] == ["field:isLifeInsured"]
    assert report.affected_decisions == ["business-field-definitions.decision-2"]


def test_routing_positional_rebuild_for_chunk_consumer(tmp_path):
    path = _write(tmp_path, "enums.yaml", _CHUNK_YAML)
    changed = _write(tmp_path, "changed.yaml", _CHUNK_YAML.replace("产品D", "产品E"))
    report = detect_ref_drift(
        ref_id="business-planfullname-enums",
        path=changed,
        declared_sha256=file_sha256(path),
        consumption=[{"consumer": "planfullname_index", "mode": "positional_frozen"}],
        navigation_entry_keys=["values-0000-0001", "values-0002-0003"],
    )
    assert report.routing == ROUTING_POSITIONAL_REBUILD
    assert report.affected_key_index_entries == ["values-0000-0001", "values-0002-0003"]


def test_routing_unregistered_fails_closed(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    changed = _write(tmp_path, "changed.yaml", _FIELD_YAML.replace("true", "false", 1))
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
    )
    assert report.routing == ROUTING_NEEDS_REVIEW
    assert "no registered consumers" in report.reason


def test_apply_policy_strict_raises_and_warn_records(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    changed = _write(tmp_path, "changed.yaml", _FIELD_YAML.replace("true", "false", 1))
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
    )
    with pytest.raises(StalenessPolicyViolation):
        apply_staleness_policy(report, "strict")
    result = apply_staleness_policy(report, "warn")
    assert result["routing"] == ROUTING_ABSORB
    assert result["warnings"][0]["report"]["ref_id"] == "business-field-definitions"


def test_apply_policy_clean_passes_strict(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=path,
        declared_sha256=file_sha256(path),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
    )
    result = apply_staleness_policy(report, "strict")
    assert result["routing"] == ROUTING_CLEAN
    assert result["warnings"] == []


def test_normalize_consumption_rejects_unknown_mode():
    with pytest.raises(ValueError):
        normalize_consumption([{"consumer": "x", "mode": "magic"}])
    assert normalize_consumption([{"consumer": "x", "mode": "key_live"}]) == [
        {"consumer": "x", "mode": "key_live"}
    ]


def test_audit_record_shape(tmp_path):
    path = _write(tmp_path, "f.yaml", _FIELD_YAML)
    changed = _write(tmp_path, "changed.yaml", _FIELD_YAML.replace("true", "false", 1))
    report = detect_ref_drift(
        ref_id="business-field-definitions",
        path=changed,
        declared_sha256=file_sha256(path),
        consumption=[{"consumer": "field_tools", "mode": "key_live"}],
    )
    from impl.core.source_staleness import build_audit_record

    record = build_audit_record(
        ref_id="business-field-definitions",
        action="auto_absorb",
        report=report,
        outcome={"manifest_sha256_changed": True},
    )
    assert record["action"] == "auto_absorb"
    assert record["actual_sha256"] != record["declared_sha256"]
    assert json.dumps(record, ensure_ascii=False)


def test_embedding_cache_keyed_refresh_only_embeds_changed_entries(tmp_path, monkeypatch):
    """Q5b: entry-keyed embedding rebuild touches only changed projections."""
    from impl.core.schema import InvestigationKeyEntry
    from impl.projects.client_search.draft import simulate_field_key_index as sim

    monkeypatch.setattr(sim, "EMBEDDING_CACHE_PATH", tmp_path / "cache.json")
    captured: list[list[str]] = []

    class FakeProvider:
        model_id = "fake-bailian"

        def embed(self, texts):
            captured.append(list(texts))
            return [[float(index + 1), 0.0] for index in range(len(texts))]

    monkeypatch.setattr(sim, "BailianEmbeddingProvider", lambda: FakeProvider())

    def entry(key, text):
        return InvestigationKeyEntry(key=key, name=key, search_text=text, target_ref=f"t/{key}")

    probes = [{"id": "q1", "query": "query one"}]
    first = [entry("a", "alpha"), entry("b", "beta")]
    cache = sim._refresh_embedding_cache(first, probes)
    assert sorted(cache["entry_sha256"]) == ["a", "b"]
    assert len(captured) == 2  # baseline: entries + queries

    captured.clear()
    second = [entry("a", "alpha"), entry("b", "BETA-changed")]
    refreshed = sim._refresh_embedding_cache(second, probes, existing=cache)
    # only entry b was re-embedded; queries unchanged are carried over
    assert captured == [["字段标识: b\n字段名称: b\n检索说明: BETA-changed"]]
    assert refreshed["entry_vectors"]["a"] == cache["entry_vectors"]["a"]
    assert refreshed["entry_vectors"]["b"] != cache["entry_vectors"]["b"]
    assert refreshed["query_vectors"] == cache["query_vectors"]


def test_large_material_without_retrieval_channel_is_reported(tmp_path):
    from impl.core.source_staleness import audit_large_materials_without_retrieval_channel

    big = tmp_path / "big.yaml"
    big.write_text("x" * 40000, encoding="utf-8")
    small = tmp_path / "small.yaml"
    small.write_text("x" * 100, encoding="utf-8")

    manifest = {
        "evidence_refs": [
            {
                "ref_id": "business-big",
                "location": {"location": "big.yaml", "location_scope": "business_source"},
                "metadata": {},
            },
            {
                "ref_id": "business-small",
                "location": {"location": "small.yaml", "location_scope": "business_source"},
                "metadata": {},
            },
            {
                "ref_id": "business-big-indexed",
                "location": {"location": "big.yaml", "location_scope": "business_source"},
                "metadata": {"consumption": [{"consumer": "field-key-index", "mode": "key_live"}]},
            },
            {
                "ref_id": "project-doc",
                "location": {"location": "doc.md", "location_scope": "project_package"},
                "metadata": {},
            },
        ]
    }
    findings = audit_large_materials_without_retrieval_channel(
        manifest,
        tmp_path,
        threshold_chars=30000,
    )
    assert [item["ref_id"] for item in findings] == ["business-big"]
    assert findings[0]["size_chars"] == 40000
    assert findings[0]["severity"] == "high"


def test_large_declared_source_not_in_manifest_is_reported(tmp_path):
    from impl.core.source_staleness import audit_large_materials_without_retrieval_channel

    big = tmp_path / "abbrname_enums.yaml"
    big.write_text("x" * 50000, encoding="utf-8")
    manifest = {"evidence_refs": []}
    findings = audit_large_materials_without_retrieval_channel(
        manifest,
        tmp_path,
        threshold_chars=30000,
        declared_sources={"abbrname_enums": big},
    )
    assert len(findings) == 1
    assert findings[0]["logical_name"] == "abbrname_enums"
    assert findings[0]["ref_id"] is None
    assert findings[0]["size_chars"] == 50000


def test_registered_large_source_not_duplicated_by_declared_sources(tmp_path):
    from impl.core.source_staleness import audit_large_materials_without_retrieval_channel

    big = tmp_path / "field_definitions.yaml"
    big.write_text("x" * 50000, encoding="utf-8")
    manifest = {
        "evidence_refs": [
            {
                "ref_id": "business-field-definitions",
                "location": {
                    "location": "field_definitions.yaml",
                    "location_scope": "business_source",
                },
                "metadata": {"consumption": [{"consumer": "field-key-index", "mode": "key_live"}]},
            }
        ]
    }
    findings = audit_large_materials_without_retrieval_channel(
        manifest,
        tmp_path,
        threshold_chars=30000,
        declared_sources={"field_definitions": big},
    )
    assert findings == []
