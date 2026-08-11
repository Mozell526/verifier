"""Core 后处理测试：assessment 的 authority_tool_call_ids 消费规则（authority.md §8）。"""
from __future__ import annotations

from impl.core.authority_gate import apply_authority_gate
from impl.core.schema import (
    AuthorityResolution,
    BusinessExpectation,
    FulfillmentAssessment,
    JudgeResult,
)


def _result(*assessments: FulfillmentAssessment) -> JudgeResult:
    return JudgeResult(
        trace_id="t1",
        project_id="client_search",
        business_expectations=[
            BusinessExpectation(expectation_id="e1", blocking=True),
        ],
        fulfillment_assessments=list(assessments),
    )


def _assessment(expectation_id: str, status: str, call_ids=()) -> FulfillmentAssessment:
    return FulfillmentAssessment(
        expectation_id=expectation_id,
        status=status,
        authority_tool_call_ids=list(call_ids),
    )


def test_no_calls_untouched():
    result = _result(_assessment("e1", "fulfilled"))
    out = apply_authority_gate(result, {})
    assert out.fulfillment_assessments[0].status == "fulfilled"


def test_missing_reference_marks_needs_human_review():
    result = _result(_assessment("e1", "fulfilled", ["tc-missing"]))
    out = apply_authority_gate(result, {})
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    kinds = [item.get("kind") for item in assessment.evidence_refs]
    assert "authority_reference_missing" in kinds
    marker = next(item for item in assessment.evidence_refs if item.get("kind") == "authority_reference_missing")
    assert marker.get("needs_human_review") is True


def test_unresolved_forces_not_evaluable_and_attaches_evidence():
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="unresolved",
                statement="",
                reason="两份资料在相同决定范围内冲突。",
                basis_evidence_ref_ids=("ref-a", "ref-b"),
                required_evidence=("当前生效版本",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-1"]))
    out = apply_authority_gate(result, audit)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    entry = next(item for item in assessment.evidence_refs if item.get("kind") == "authority_unresolved")
    assert entry["reason"] == "两份资料在相同决定范围内冲突。"
    assert entry["basis_evidence_ref_ids"] == ["ref-a", "ref-b"]
    assert entry["required_evidence"] == ["当前生效版本"]
    assert entry["environment_snapshot_sha256"] == "snap-1"


def test_resolved_does_not_override_judge():
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="resolved",
                statement="采用正式规范 v3。",
                reason="发布资料声明 supersedes。",
                basis_evidence_ref_ids=("ref-a",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-1"]))
    out = apply_authority_gate(result, audit)
    assert out.fulfillment_assessments[0].status == "fulfilled"


def test_tool_failure_forces_not_evaluable_with_capability_unavailable():
    """§8.4：工具执行失败（能力不可用）→ not_evaluable，原因写"Authority 能力不可用"。

    与"真查证过仍 unresolved"区分：工具失败不是业务裁决结果，不携带 resolution，
    也不标 needs_human_review（不是静默放行，是真实执行失败）。
    """
    audit = {
        "tc-fail": {
            "request": {"decision_question": "客户搜索产品是否支持按车牌查询？"},
            "tool_failure": True,
            "error": "RuntimeError: rpm exhausted",
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-fail"]))
    out = apply_authority_gate(result, audit)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    entry = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "authority_tool_failure"
    )
    assert "Authority 能力不可用" in entry["reason"]
    assert "rpm exhausted" in entry["reason"]
    assert entry.get("needs_human_review") is not True
    assert entry["environment_snapshot_sha256"] == "snap-1"


def test_unrelated_assessment_not_blocked():
    """§9：与 unresolved Authority 无关的 expectation 不受阻断。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="unresolved",
                statement="",
                reason="高净值定义冲突。",
                basis_evidence_ref_ids=("ref-a",),
                required_evidence=("正式定义",),
            ),
        }
    }
    result = _result(
        _assessment("e-high", "fulfilled", ["tc-1"]),
        _assessment("e-age", "fulfilled", []),
    )
    out = apply_authority_gate(result, audit)
    by_id = {item.expectation_id: item for item in out.fulfillment_assessments}
    assert by_id["e-high"].status == "not_evaluable"
    assert by_id["e-age"].status == "fulfilled"


def test_ne_capability_boundary_without_authority_flags_human_review():
    """§8.4：NE 且成因=职责外/能力边界，但没有 authority 调用记录 → needs_human_review。"""
    assessment = FulfillmentAssessment(
        expectation_id="e1",
        status="not_evaluable",
        actual_evidence=[
            "结论类型：职责外；产品不支持按车牌查询",
        ],
    )
    out = apply_authority_gate(_result(assessment), {})
    result_assessment = out.fulfillment_assessments[0]
    marker = next(
        item for item in result_assessment.evidence_refs
        if item.get("kind") == "authority_required_not_consulted"
    )
    assert marker.get("needs_human_review") is True


def test_ne_insufficient_evidence_without_authority_flags_human_review():
    """§8.4：NE 且成因=依据不充分（无 authority 记录）→ needs_human_review。"""
    assessment = FulfillmentAssessment(
        expectation_id="e1",
        status="not_evaluable",
        actual_evidence=["结论类型：依据不充分；无法确认请求概念是否在清单内"],
    )
    out = apply_authority_gate(_result(assessment), {})
    kinds = [item.get("kind") for item in out.fulfillment_assessments[0].evidence_refs]
    assert "authority_required_not_consulted" in kinds


def test_ne_input_bad_or_unrelated_without_authority_not_flagged():
    """§8.1：输入坏/完全无关两类 NE 不依赖 Authority，不受硬校验约束。"""
    cases = (
        ["结论类型：输入坏；用户输入无效，无法解析查询条件"],
        ["结论类型：完全无关；该请求与客户搜索无关"],
    )
    for evidence in cases:
        assessment = FulfillmentAssessment(
            expectation_id="e1",
            status="not_evaluable",
            actual_evidence=list(evidence),
        )
        out = apply_authority_gate(_result(assessment), {})
        kinds = [item.get("kind") for item in out.fulfillment_assessments[0].evidence_refs]
        assert "authority_required_not_consulted" not in kinds
        assert "not_evaluable_cause_missing" not in kinds


def test_ne_without_explicit_cause_tag_fail_closed():
    """无显式「结论类型：」标记的 NE：成因无法程序化确认，fail-closed 要求人审。"""
    assessment = FulfillmentAssessment(
        expectation_id="e1",
        status="not_evaluable",
        actual_evidence=["该维度属于系统能力边界外，产品不支持按车牌查询"],
    )
    out = apply_authority_gate(_result(assessment), {})
    marker = next(
        item for item in out.fulfillment_assessments[0].evidence_refs
        if item.get("kind") == "not_evaluable_cause_missing"
    )
    assert marker.get("needs_human_review") is True


def test_empty_ne_cause_fail_closed():
    """空 evidence 不能绕过 fulfilled.md §2.3 的成因说明要求。"""
    assessment = FulfillmentAssessment(
        expectation_id="e1",
        status="not_evaluable",
    )

    out = apply_authority_gate(_result(assessment), {})

    marker = next(
        item for item in out.fulfillment_assessments[0].evidence_refs
        if item.get("kind") == "not_evaluable_cause_missing"
    )
    assert marker.get("needs_human_review") is True


def test_ne_with_unresolved_authority_record_derives_cause():
    """§8.4：not_evaluable 且已真实调用 authority（unresolved）→ 成因由审计派生，
    不要求 judge 复述「结论类型：」标记；有查证记录不是静默放行（audit 可见）。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="unresolved",
                statement="",
                reason="当前资料无法证明该能力存在或缺失。",
                basis_evidence_ref_ids=("ref-a",),
                required_evidence=("能力清单",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    assessment = FulfillmentAssessment(
        expectation_id="e1",
        status="not_evaluable",
        actual_evidence=["无法确认请求概念是否在清单内，依据不充分"],
        authority_tool_call_ids=["tc-1"],
    )
    out = apply_authority_gate(_result(assessment), audit)
    kinds = [item.get("kind") for item in out.fulfillment_assessments[0].evidence_refs]
    assert "not_evaluable_cause_missing" not in kinds
    assert "authority_required_not_consulted" not in kinds
    assert "authority_unresolved" in kinds
    assert not any(
        item.get("needs_human_review") is True
        for item in out.fulfillment_assessments[0].evidence_refs
    )


def test_ne_with_supported_authority_record_keeps_human_review():
    """authority 已 resolved/supported（确定性裁决）但 judge 仍判 not_evaluable：
    成因无法从审计派生（不是依据不充分），保持 needs_human_review 不静默放行。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="resolved",
                statement="产品支持该字段搜索。",
                reason="字段定义明确登记可搜索。",
                basis_evidence_ref_ids=("ref-a",),
                required_evidence=(),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    assessment = FulfillmentAssessment(
        expectation_id="e1",
        status="not_evaluable",
        actual_evidence=["无法判断是否满足"],
        authority_tool_call_ids=["tc-1"],
    )
    out = apply_authority_gate(_result(assessment), audit)
    kinds = [item.get("kind") for item in out.fulfillment_assessments[0].evidence_refs]
    assert "not_evaluable_cause_missing" in kinds
    assert any(
        item.get("needs_human_review") is True
        for item in out.fulfillment_assessments[0].evidence_refs
    )


def test_forged_numeric_resolution_id_gets_diagnostic_hint():
    """旧行为编造的数字决议 id（如 "8"）仍是非法引用 → needs_human_review + 诊断。"""
    result = _result(_assessment("e1", "not_evaluable", ["8"]))
    out = apply_authority_gate(result, {})
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    marker = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "authority_reference_missing"
    )
    assert marker.get("needs_human_review") is True
    assert "决议" in marker["reason"]


def test_uninjected_audit_ref_gets_diagnostic_hint():
    """resolution.N@<hash12> 形态但未注入的引用 → needs_human_review + 诊断。"""
    result = _result(
        _assessment("e1", "not_evaluable", ["resolution.8@deadbeefcafe"])
    )
    out = apply_authority_gate(result, {})
    marker = next(
        item for item in out.fulfillment_assessments[0].evidence_refs
        if item.get("kind") == "authority_reference_missing"
    )
    assert marker.get("needs_human_review") is True
    assert "audit_ref" in marker["reason"]


def test_claim_mode_gap_only_forces_not_evaluable():
    """grill/authority.md §2.2：claim 担保模式 gap_only 与 unresolved 同口径。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="gap_only",
                statement="",
                reason="存在管辖资料但缺少决定性操作符形态证据。",
                basis_evidence_ref_ids=("ref-a",),
                required_evidence=("操作符形态的正式裁决或覆盖声明",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-1"]))
    out = apply_authority_gate(result, audit)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    entry = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "authority_unresolved"
    )
    assert entry["resolution_status"] == "gap_only"
    assert entry["required_evidence"] == ["操作符形态的正式裁决或覆盖声明"]


def test_claim_mode_ungoverned_forces_not_evaluable():
    """grill/authority.md §2.2：claim 担保模式 ungoverned 与 unresolved 同口径。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="ungoverned",
                statement="",
                reason="当前证据空间没有资料管辖该主题。",
                basis_evidence_ref_ids=(),
                required_evidence=("补充能够管辖该主题的权威资料",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-1"]))
    out = apply_authority_gate(result, audit)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    entry = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "authority_unresolved"
    )
    assert entry["resolution_status"] == "ungoverned"


def test_claim_mode_contradicted_blocks_affirmative_and_marks_human_review():
    """grill/authority.md §4.2-2：contradicted 的肯定性 verdict 不得成立 + 人审。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="contradicted",
                statement="资料结论与 claim 相反。",
                reason="已加载资料明确给出相反口径。",
                basis_evidence_ref_ids=("ref-a",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-1"]))
    out = apply_authority_gate(result, audit)
    assessment = out.fulfillment_assessments[0]
    assert assessment.status == "not_evaluable"
    entry = next(
        item for item in assessment.evidence_refs
        if item.get("kind") == "authority_contradicted"
    )
    assert entry["needs_human_review"] is True

    negative = _result(_assessment("e1", "not_fulfilled", ["tc-1"]))
    out_negative = apply_authority_gate(negative, audit)
    assert out_negative.fulfillment_assessments[0].status == "not_fulfilled"


def test_claim_mode_supported_does_not_override_judge():
    """grill/authority.md §2.2：supported 与 resolved 一样不覆盖 Judge。"""
    audit = {
        "tc-1": {
            "resolution": AuthorityResolution(
                status="supported",
                statement="断言获得资料担保。",
                reason="资料结论与 claim 一致。",
                basis_evidence_ref_ids=("ref-a",),
            ),
            "environment_snapshot_sha256": "snap-1",
        }
    }
    result = _result(_assessment("e1", "fulfilled", ["tc-1"]))
    out = apply_authority_gate(result, audit)
    assert out.fulfillment_assessments[0].status == "fulfilled"


# ---- fulfilled.md §3 / authority.md §8.3：resolved 能力/职责边界三态消费 ----


def _boundary_audit(status: str, statement: str, call_id: str = "tc-b") -> dict:
    return {
        call_id: {
            "resolution": AuthorityResolution(
                status=status,
                statement=statement,
                reason="依据字段定义与证明范围合同裁决。",
                basis_evidence_ref_ids=("ref-a",),
                required_evidence=(),
            ),
            "environment_snapshot_sha256": "snap-b",
        }
    }


def test_boundary_outside_forces_not_evaluable_whatever_judge_says():
    """§8.3：statement=职责外 → 无论 judge 判 fulfilled/not_fulfilled 都落说不清。"""
    audit = _boundary_audit(
        "supported", "职责外：产品不支持按公司名称查询客户，不在职责范围。"
    )
    for judge_status in ("fulfilled", "not_fulfilled"):
        out = apply_authority_gate(
            _result(_assessment("e1", judge_status, ["tc-b"])), audit
        )
        a = out.fulfillment_assessments[0]
        assert a.status == "not_evaluable", f"judge={judge_status}"
        kinds = [e.get("kind") for e in (a.evidence_refs or [])]
        assert "authority_boundary_outside" in kinds
        assert "not_evaluable_cause_missing" not in kinds


def test_boundary_outside_keeps_judge_ne_without_human_review():
    """§8.3：judge 已判 ne + 职责外裁决 → 保持 ne，成因由审计派生，不误伤人审。"""
    audit = _boundary_audit(
        "supported", "职责外：产品不支持按公司名称查询客户，不在职责范围。"
    )
    out = apply_authority_gate(
        _result(_assessment("e1", "not_evaluable", ["tc-b"])), audit
    )
    a = out.fulfillment_assessments[0]
    assert a.status == "not_evaluable"
    assert not any(
        e.get("needs_human_review") is True for e in (a.evidence_refs or [])
    )


def test_capability_gap_converts_judge_ne_to_not_fulfilled():
    """§8.3：statement=职责内能力缺失 → 不得降 ne；功能未实现=没办成。"""
    audit = _boundary_audit(
        "supported", "职责内能力缺失：customerReview 字段不支持搜索，功能未实现。"
    )
    out = apply_authority_gate(
        _result(_assessment("e1", "not_evaluable", ["tc-b"])), audit
    )
    a = out.fulfillment_assessments[0]
    assert a.status == "not_fulfilled"
    kinds = [e.get("kind") for e in (a.evidence_refs or [])]
    assert "authority_capability_gap" in kinds
    assert "not_evaluable_cause_missing" not in kinds


def test_capability_gap_keeps_judge_not_fulfilled():
    """§8.3：judge 已按职责内能力缺失判 not_fulfilled → 保持，不覆盖。"""
    audit = _boundary_audit(
        "supported", "职责内能力缺失：customerReview 字段不支持搜索，功能未实现。"
    )
    out = apply_authority_gate(
        _result(_assessment("e1", "not_fulfilled", ["tc-b"])), audit
    )
    assert out.fulfillment_assessments[0].status == "not_fulfilled"


def test_capability_gap_does_not_override_unresolved_driven_ne():
    """职责内能力缺失 + 同 assessment 还消费了 unresolved 类调用 → 以依据不充分为准 ne。"""
    audit = {
        "tc-b": _boundary_audit(
            "supported", "职责内能力缺失：customerReview 字段不支持搜索。"
        )["tc-b"],
        "tc-u": {
            "resolution": AuthorityResolution(
                status="unresolved",
                statement="",
                reason="资料冲突，无法确认。",
                basis_evidence_ref_ids=(),
                required_evidence=("决定性资料",),
            ),
            "environment_snapshot_sha256": "snap-u",
        },
    }
    out = apply_authority_gate(
        _result(_assessment("e1", "not_evaluable", ["tc-b", "tc-u"])), audit
    )
    a = out.fulfillment_assessments[0]
    assert a.status == "not_evaluable"
    assert any(
        e.get("kind") == "authority_unresolved" for e in (a.evidence_refs or [])
    )


def test_within_scope_does_not_override():
    """§8.3：statement=职责内正常 → 不覆盖 judge 判定。"""
    audit = _boundary_audit(
        "supported", "职责内正常：该字段属于职责且能力可用。"
    )
    out = apply_authority_gate(
        _result(_assessment("e1", "fulfilled", ["tc-b"])), audit
    )
    assert out.fulfillment_assessments[0].status == "fulfilled"
