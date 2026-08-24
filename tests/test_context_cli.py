from __future__ import annotations

import json

from impl.context.__main__ import audit_project_context, main
from impl.core.schema.context import ContextRecord


def test_context_init_without_project_adapter_exits_safely(tmp_path, capsys):
    main(["init", "--project", "QA", "--data-root", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["project_id"] == "QA"
    assert payload["adapter_count"] == 0
    assert payload["record_count"] == 0
    assert payload["project_adapters"] == []
    assert payload["message"] == "project has no configured context units yet"


def test_context_audit_uses_persisted_governance_report(monkeypatch):
    persisted = {
        "snapshot": {"compiled_prompt_sha256": "abc"},
        "findings": [],
        "gate": {"mode": "production", "blocking": False},
    }
    monkeypatch.setattr(
        "impl.context.__main__.load_contexts_by_trace",
        lambda project_id, trace_id: [ContextRecord(
            record_id="record-1",
            trace_id=trace_id,
            project_id=project_id,
            caller="judge",
            messages=[{"role": "system", "content": "prompt"}],
            created_at="2026-08-08T00:00:00Z",
            prompt_size=6,
            governance=persisted,
        )],
    )

    result = audit_project_context("demo", "trace-1")

    assert result["record_id"] == "record-1"
    assert result["governance"] == persisted


def test_context_audit_marks_historical_records_as_limited(monkeypatch):
    monkeypatch.setattr(
        "impl.context.__main__.load_contexts_by_trace",
        lambda project_id, trace_id: [ContextRecord(
            record_id="legacy",
            trace_id=trace_id,
            project_id=project_id,
            caller="judge",
            messages=[
                {"role": "system", "content": "legacy prompt"},
                {"role": "user", "content": "{}"},
            ],
        )],
    )

    result = audit_project_context("demo", "trace-legacy")

    assert {item["code"] for item in result["governance"]["findings"]} == {
        "output_contract_count",
        "historical_provenance_unavailable",
    }
