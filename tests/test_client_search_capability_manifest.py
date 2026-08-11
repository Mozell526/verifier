from __future__ import annotations

from pathlib import Path

import pytest

from impl.projects.client_search.capability_manifest import build_capability_manifest


def test_repeated_field_merges_every_inline_and_referenced_enum(tmp_path: Path):
    definitions = tmp_path / "definitions.yaml"
    enums = tmp_path / "enums.yaml"
    definitions.write_text(
        """intents:
  - field: product
    operator: MATCH
    value_type: enum
    enum_ref: products_a
  - field: product
    operator: CONTAINS
    value_type: enum_list
    enum_ref: products_b
    enum: [inline]
""",
        encoding="utf-8",
    )
    enums.write_text(
        "products_a: {values: [a, shared]}\nproducts_b: {values: [b, shared]}\n",
        encoding="utf-8",
    )

    manifest = build_capability_manifest(definitions, enums)

    assert manifest["product"]["enums"] == ["a", "shared", "inline", "b"]
    assert manifest["product"]["enum_refs"] == ["products_a", "products_b"]
    assert manifest["product"]["unresolved_enum_refs"] == []


def test_explicit_missing_enum_registry_fails_closed(tmp_path: Path):
    definitions = tmp_path / "definitions.yaml"
    definitions.write_text("intents: []\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="enum registry not found"):
        build_capability_manifest(definitions, tmp_path / "missing.yaml")


def test_unknown_enum_ref_remains_visible_in_manifest(tmp_path: Path):
    definitions = tmp_path / "definitions.yaml"
    enums = tmp_path / "enums.yaml"
    definitions.write_text(
        "intents:\n  - field: product\n    operator: MATCH\n    enum_ref: absent\n",
        encoding="utf-8",
    )
    enums.write_text("known: {values: [a]}\n", encoding="utf-8")

    manifest = build_capability_manifest(definitions, enums)

    assert manifest["product"]["unresolved_enum_refs"] == ["absent"]


def test_multiple_enum_files_merge_into_one_registry(tmp_path: Path):
    definitions = tmp_path / "definitions.yaml"
    base_enums = tmp_path / "base_enums.yaml"
    extra_enums = tmp_path / "extra_enums.yaml"
    definitions.write_text(
        "intents:\n"
        "  - field: planfullname\n"
        "    operator: MATCH\n"
        "    value_type: enum\n"
        "    enum_ref: polNoInfo.plancodeinfo.planfullname\n"
        "  - field: profName\n"
        "    operator: MATCH\n"
        "    value_type: enum\n"
        "    enum_ref: profName\n",
        encoding="utf-8",
    )
    base_enums.write_text(
        "clientSex: {values: [男, 女]}\n",
        encoding="utf-8",
    )
    extra_enums.write_text(
        "polNoInfo.plancodeinfo.planfullname:\n"
        "  values: [住院医疗保险, 平安e生保医疗保险]\n"
        "profName:\n"
        "  values: [航天工程技术人员, 企业负责人]\n",
        encoding="utf-8",
    )

    manifest = build_capability_manifest(
        definitions,
        enums_path=[base_enums, extra_enums],
    )

    assert manifest["planfullname"]["unresolved_enum_refs"] == []
    assert manifest["planfullname"]["enums"] == ["住院医疗保险", "平安e生保医疗保险"]
    assert manifest["profName"]["unresolved_enum_refs"] == []
    assert manifest["profName"]["enums"] == ["航天工程技术人员", "企业负责人"]


def test_missing_extra_enum_file_fails_closed(tmp_path: Path):
    definitions = tmp_path / "definitions.yaml"
    definitions.write_text("intents: []\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="enum registry not found"):
        build_capability_manifest(
            definitions,
            enums_path=[tmp_path / "missing_extra.yaml"],
        )


def test_is_supported_is_preserved_and_false_wins_across_field_entries(tmp_path: Path):
    definitions = tmp_path / "definitions.yaml"
    definitions.write_text(
        "intents:\n"
        "  - field: customerReview\n"
        "    operator: MATCH\n"
        "    is_supported: false\n"
        "  - field: customerReview\n"
        "    operator: EXISTS\n"
        "  - field: supportedField\n"
        "    operator: MATCH\n"
        "    is_supported: true\n"
        "  - field: defaultSupportedField\n"
        "    operator: MATCH\n",
        encoding="utf-8",
    )

    manifest = build_capability_manifest(definitions)

    assert manifest["customerReview"]["is_supported"] is False
    assert manifest["customerReview"]["is_supported_explicit"] is True
    assert manifest["supportedField"]["is_supported"] is True
    assert manifest["supportedField"]["is_supported_explicit"] is True
    assert manifest["defaultSupportedField"]["is_supported"] is True
    assert manifest["defaultSupportedField"]["is_supported_explicit"] is False
