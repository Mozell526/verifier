"""AuthorityTool 工具失败语义测试（authority.md §8.4）。

工具执行失败（能力不可用，如限流/异常）必须落 audit（tool_failure 标记 +
错误信息）并返回结构化 tool_failure 结果给调用方 LLM；不得把失败当作业务
unresolved 或伪造成资料冲突。
"""
from __future__ import annotations

import pytest

from impl.core import authority_tool as authority_tool_module
from impl.core.authority_tool import AuthorityTool


class _FakeEnv:
    project_id = "client_search"
    environment_snapshot_sha256 = "snap-1"


def test_execute_failure_writes_audit_and_returns_tool_failure(monkeypatch):
    def boom(env, request, *, llm=None, authority_call_id=""):
        raise RuntimeError("rpm exhausted")

    monkeypatch.setattr(authority_tool_module, "resolve_authority", boom)
    tool = AuthorityTool(_FakeEnv())
    result = tool._execute("客户搜索产品是否支持按车牌查询？")

    assert result["status"] == "tool_failure"
    assert result["statement"] == ""
    assert "Authority 能力不可用" in result["reason"]
    assert result["tool_call_id"].startswith("authority.client_search.")

    audit = tool.audit[result["tool_call_id"]]
    assert audit["tool_failure"] is True
    assert "rpm exhausted" in audit["error"]
    assert audit["environment_snapshot_sha256"] == "snap-1"
    # 业务 unresolved 与工具失败分开：失败不携带 resolution
    assert "resolution" not in audit


def test_execute_failure_is_cached_like_success(monkeypatch):
    calls = {"count": 0}

    def boom(env, request, *, llm=None, authority_call_id=""):
        calls["count"] += 1
        raise ValueError("boom")

    monkeypatch.setattr(authority_tool_module, "resolve_authority", boom)
    tool = AuthorityTool(_FakeEnv())
    first = tool._execute("同一问题？")
    second = tool._execute("同一问题？")

    assert first["tool_call_id"] == second["tool_call_id"]
    assert len(tool.audit) == 1
    assert calls["count"] == 1


def test_execute_failure_empty_question_still_raises(monkeypatch):
    tool = AuthorityTool(_FakeEnv())
    with pytest.raises(ValueError, match="non-empty"):
        tool._execute("   ")


def test_claim_participates_in_cache_and_audit(monkeypatch):
    from impl.core.schema import AuthorityIndependentResolution, AuthorityResolution

    calls = {"count": 0}

    def resolve(env, request, *, llm=None, authority_call_id=""):
        calls["count"] += 1
        independent = AuthorityIndependentResolution(
            status="resolved",
            statement="A",
            reason="blind",
            basis_evidence_ref_ids=("ref-1",),
        )
        return AuthorityResolution(
            status="supported",
            statement="A",
            reason="match",
            basis_evidence_ref_ids=("ref-1",),
            independent_resolution=independent,
        )

    monkeypatch.setattr(authority_tool_module, "resolve_authority", resolve)
    tool = AuthorityTool(_FakeEnv())
    claim_a = {
        "claim_statement": "A",
        "subject": {"kind": "rule", "id": "x"},
        "conclusion_kind": "normative_rule",
        "intended_use": "expectation-1",
    }
    claim_b = {**claim_a, "claim_statement": "B"}

    first = tool._execute("A 还是 B？", claim_a)
    duplicate = tool._execute("A 还是 B？", claim_a)
    different = tool._execute("A 还是 B？", claim_b)

    assert duplicate["tool_call_id"] == first["tool_call_id"]
    assert different["tool_call_id"] != first["tool_call_id"]
    assert calls["count"] == 2
    audit = tool.audit[first["tool_call_id"]]
    assert audit["request"]["claim"] == claim_a
    assert audit["independent_resolution"].status == "resolved"


def test_tool_schema_rejects_extra_arguments_and_documents_strict_json():
    tool = AuthorityTool(_FakeEnv()).as_verifiable_tool()

    assert tool.parameters["additionalProperties"] is False
    assert tool.parameters["properties"]["claim"]["additionalProperties"] is False
    assert "严格 JSON" in tool.description
    assert "supported/contradicted/ungoverned/gap_only" in tool.description
