from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from impl.core.context_governance import (
    ContextGovernanceBlocked,
    build_context_governance_report,
    configure_context_governance,
    ensure_call_context_governance,
    governance_report_matches_call,
    slice_context_clauses,
    transition_context_finding,
)
from impl.core.structured_output import StructuredOutputSpec


@dataclass
class _Output:
    result: str


@dataclass
class _Assessment:
    status: str


@dataclass
class _NestedOutput:
    fulfillment_assessments: List[_Assessment] = field(default_factory=list)


OUTPUT_SPEC = StructuredOutputSpec.from_dataclass(
    _Output,
    required_nonempty=["result"],
    description="test output",
)


def _report(system: str, **overrides):
    values = {
        "project_id": "demo",
        "role": "judge",
        "stage": "judge",
        "mode": "draft",
        "system": system,
        "user": "{}",
        "output_spec": OUTPUT_SPEC,
        "segments": [
            {
                "segment_id": "project-rules",
                "source": "project://judge.md",
                "content": system,
            }
        ],
        "runtime_owned_fields": ["actual", "overall_fulfillment"],
    }
    values.update(overrides)
    return build_context_governance_report(**values)


def test_snapshot_records_replay_identities_without_copying_prompt_text():
    report = _report("顶层只允许 result。")

    snapshot = report["snapshot"]
    assert report["gate"]["blocking"] is False
    assert snapshot["output_contract"]["identity"].endswith("._Output")
    assert snapshot["output_contract"]["sha256"]
    assert snapshot["compiled_prompt_sha256"]
    assert snapshot["segments"][0]["source"] == "project://judge.md"
    assert "content" not in snapshot["segments"][0]


def test_scanner_blocks_runtime_owned_field_claimed_by_llm():
    report = _report("顶层只允许 result、actual。")

    assert report["gate"]["blocking"] is True
    finding = next(
        item for item in report["findings"]
        if item["code"] == "runtime_field_claimed_by_llm"
    )
    assert finding["severity"] == "blocking"
    assert finding["owner"]["primary"] == "project_compiler"
    assert finding["evidence"][0]["fields"] == ["actual"]


def test_scanner_distinguishes_nested_field_ownership_paths():
    nested_spec = StructuredOutputSpec.from_dataclass(_NestedOutput)
    report = _report(
        "fulfillment_assessments 只能产 status / confidence。",
        output_spec=nested_spec,
        runtime_owned_fields=["fulfillment_assessments[*].confidence"],
    )

    finding = next(
        item for item in report["findings"]
        if item["code"] == "runtime_field_claimed_by_llm"
    )
    assert finding["evidence"][0]["fields"] == [
        "fulfillment_assessments[*].confidence"
    ]


def test_scanner_blocks_schema_field_forbidden_by_prompt():
    report = _report("不要输出 result。")

    assert any(
        item["code"] == "schema_field_forbidden_by_prompt"
        for item in report["findings"]
    )


def test_draft_gate_fails_before_call_but_production_only_records_diagnostic():
    class Client:
        pass

    draft = Client()
    with pytest.raises(ContextGovernanceBlocked):
        configure_context_governance(
            draft,
            config={
                "enabled": True,
                "mode": "draft",
                "runtime_owned_fields": ["actual"],
                "compiler_source": "project://compiler",
            },
            project_id="demo",
            system="顶层只允许 result、actual。",
            user="{}",
            output_spec=OUTPUT_SPEC,
        )
    assert draft._context_governance_report["gate"]["blocking"] is True

    production = Client()
    report = configure_context_governance(
        production,
        config={
            "enabled": True,
            "mode": "production",
            "runtime_owned_fields": ["actual"],
            "compiler_source": "project://compiler",
        },
        project_id="demo",
        system="顶层只允许 result、actual。",
        user="{}",
        output_spec=OUTPUT_SPEC,
    )
    assert report["gate"] == {"mode": "production", "blocking": True}


def test_unconfigured_call_gets_production_snapshot_and_stale_snapshot_is_replaced():
    class Client:
        pass

    client = Client()
    first = ensure_call_context_governance(
        client,
        project_id="demo",
        role="attribute",
        stage="investigation",
        trace_id="trace-1",
        system="只输出 result。",
        user='{"case": 1}',
        output_spec=OUTPUT_SPEC,
        tools=[],
    )
    assert first["gate"]["mode"] == "production"
    assert first["snapshot"]["lineage"]["trace_id"] == "trace-1"
    assert governance_report_matches_call(
        first,
        system="只输出 result。",
        user='{"case": 1}',
        output_spec=OUTPUT_SPEC,
    )

    second = ensure_call_context_governance(
        client,
        project_id="demo",
        role="attribute",
        stage="investigation",
        trace_id="trace-2",
        system="只输出 result。",
        user='{"case": 2}',
        output_spec=OUTPUT_SPEC,
        tools=[],
    )
    assert second["snapshot"]["lineage"]["trace_id"] == "trace-2"
    assert second["snapshot"]["compiled_prompt_sha256"] != first["snapshot"]["compiled_prompt_sha256"]


def test_exact_draft_snapshot_is_preserved_by_global_call_guard():
    class Client:
        pass

    client = Client()
    draft = configure_context_governance(
        client,
        config={
            "enabled": True,
            "mode": "draft",
            "role": "judge",
            "stage": "judge",
            "trace_id": "trace-draft",
        },
        project_id="demo",
        system="只输出 result。",
        user="{}",
        output_spec=OUTPUT_SPEC,
    )
    guarded = ensure_call_context_governance(
        client,
        project_id="demo",
        role="judge",
        stage="judge",
        trace_id="trace-draft",
        system="只输出 result。",
        user="{}",
        output_spec=OUTPUT_SPEC,
        tools=[],
    )
    assert guarded is not draft
    assert guarded == draft
    assert guarded["gate"]["mode"] == "draft"


def test_role_and_stage_policy_are_checked_on_each_segment():
    report = _report(
        "顶层只允许 result。",
        segments=[{
            "segment_id": "attribute-private",
            "source": "project://attribute.md",
            "content": "private",
            "allowed_roles": ["attribute"],
            "allowed_stages": ["investigation"],
        }],
    )

    assert {item["code"] for item in report["findings"]} >= {
        "role_context_leak",
        "stage_context_leak",
    }


def test_scanner_blocks_missing_required_segment_protocol_mix_and_runtime_rewrite():
    report = _report(
        "顶层只允许 result。",
        required_segments=["required-business-rules"],
        segments=[{
            "segment_id": "investigation-notes",
            "source": "project://investigation.md",
            "content": "notes",
            "protocol_version": 2,
            "transform": "runtime_llm_summary",
            "runtime_visibility": "investigation_only",
        }],
    )

    assert {item["code"] for item in report["findings"]} >= {
        "required_segment_unavailable",
        "protocol_version_mismatch",
        "runtime_fact_rewrite",
        "restricted_material_in_runtime",
    }


def test_snapshot_uses_role_neutral_compiler_and_explicit_parser_identity():
    snapshot = _report("顶层只允许 result。")["snapshot"]

    assert snapshot["compiler_id"] == "context-compiler-v1"
    assert snapshot["compiler_protocol_version"] == 1
    assert snapshot["output_contract"]["parser_identity"].endswith("SchemaValidator")
    assert snapshot["output_contract"]["parser_schema_sha256"] == (
        snapshot["output_contract"]["sha256"]
    )


def test_finding_lifecycle_requires_verification_evidence():
    finding = _report("不要输出 result。")["findings"][0]
    ready = transition_context_finding(finding, to_status="remediation_ready")

    with pytest.raises(ValueError, match="requires verification evidence"):
        transition_context_finding(ready, to_status="verified")
    verified = transition_context_finding(
        ready,
        to_status="verified",
        verification_evidence=[{"kind": "scanner", "status": "passed"}],
    )
    closed = transition_context_finding(
        verified,
        to_status="closed",
        verification_evidence=[{"kind": "representative_case", "status": "passed"}],
    )
    assert closed["status"] == "closed"
    assert len(closed["verification_evidence"]) == 2


def test_project_compiler_slices_runtime_contract_clause_and_traces_exclusion():
    content = (
        "judge 输出使用 `JudgeResult` 协议字段：overall_fulfillment；"
        "application boundary 仍作为业务证据。\n"
    )

    projected, excluded = slice_context_clauses(
        content,
        source="project://judge_boundary",
        excluded_markers=["`JudgeResult` 协议字段"],
    )
    report = _report(
        projected,
        excluded_segments=excluded,
    )

    assert "JudgeResult" not in projected
    assert "application boundary" in projected
    assert report["snapshot"]["excluded_segments"][0]["source"] == "project://judge_boundary"
    assert "content" not in report["snapshot"]["excluded_segments"][0]


def test_scanner_blocks_second_inline_schema_injection():
    report = _report(
        "你将用户意图映射为 live 请求体。请求体 JSON Schema：{\"query\": \"string\"}。"
    )

    assert report["gate"]["blocking"] is True
    finding = next(
        item for item in report["findings"]
        if item["code"] == "schema_duplicate_injection"
    )
    assert finding["severity"] == "blocking"
    assert finding["evidence"][0]["inline_schema_injections"] == 1


def test_scanner_reports_manual_field_list_duplicate():
    report = _report("输出 JSON，只含 result。")

    finding = next(
        item for item in report["findings"]
        if item["code"] == "manual_field_list_duplicate"
    )
    assert finding["severity"] == "high"
    assert finding["evidence"][0]["fields"] == ["result"]


def test_scanner_reports_required_field_list_duplicate():
    report = _report("必填字段列表：result。每个必填字段都必须出现且非空；")

    finding = next(
        item for item in report["findings"]
        if item["code"] == "manual_field_list_duplicate"
    )
    assert finding["evidence"][0]["fields"] == ["result"]


def test_scanner_ignores_semantic_field_instructions():
    report = _report(
        "证据必须引用 ContextUnit；不得生成 ref_id/hash/location；分析文字必须使用中文。"
    )

    assert not any(
        item["code"] in ("schema_duplicate_injection", "manual_field_list_duplicate")
        for item in report["findings"]
    )


def test_scanner_accepts_single_rendered_contract():
    from impl.core.structured_output import render_output_constraint

    report = _report(render_output_constraint(OUTPUT_SPEC))

    assert not any(
        item["code"] in ("schema_duplicate_injection", "manual_field_list_duplicate")
        for item in report["findings"]
    )
