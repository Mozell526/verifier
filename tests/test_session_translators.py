"""spec/mock/protocol.md 6.1/6.2：多轮项目的 SessionTranslator 契约与三道自动约束。"""
from __future__ import annotations

import pytest

from impl.core.mock_protocol import MultiTurnInteractiveMock
from impl.core.project_loader import load_adapter, load_project
from impl.core.session import SessionState, SessionTranslator, UserMessage
from scripts.check_adapter_compliance import check_session_translator

MULTI_TURN_PROJECTS = ["policy_search", "marketting-planning", "deerflow"]


@pytest.mark.parametrize("project_id", MULTI_TURN_PROJECTS)
def test_multi_turn_projects_implement_translator(project_id: str) -> None:
    mock = load_adapter(load_project(project_id)).mock()
    assert isinstance(mock, MultiTurnInteractiveMock)
    assert isinstance(mock, SessionTranslator)
    assert isinstance(mock.supports_history_injection, bool)


@pytest.mark.parametrize("project_id", MULTI_TURN_PROJECTS)
def test_translator_satisfies_protocol_constraints(project_id: str) -> None:
    assert check_session_translator(project_id) == []


def test_compliance_check_flags_broken_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    from impl.projects.policy_search.mock import PolicySearchMock

    monkeypatch.setattr(
        PolicySearchMock,
        "user_message_from_request",
        lambda self, request: UserMessage(type="text", text="改写过的原话"),
    )
    violations = check_session_translator("policy_search")
    assert any("往返不变式" in reason for _, _, reason in violations)


def test_compliance_check_flags_llm_use(monkeypatch: pytest.MonkeyPatch) -> None:
    from impl.projects.deerflow.mock_base import DeerflowMockBase

    original = DeerflowMockBase.request_from_user_message

    def with_llm(self, message, state):
        from impl.core.llm_client import LlmClient

        LlmClient()
        return original(self, message, state)

    monkeypatch.setattr(DeerflowMockBase, "request_from_user_message", with_llm)
    violations = check_session_translator("deerflow")
    assert any("禁 LLM" in reason for _, _, reason in violations)


def test_policy_search_translator_injects_history_from_transcript() -> None:
    mock = load_adapter(load_project("policy_search")).mock()
    first = mock.request_from_user_message(
        UserMessage(type="text", text="保额的保单"),
        SessionState(session_id="s1", turn_index=1, transcript=[], last_request=None),
    )
    assert first["session_id"] == "s1"
    assert first["trace_id"] == "s1-turn1"
    assert first["extra_input_params"]["args"]["contexts"] == []
    second = mock.request_from_user_message(
        UserMessage(type="text", text="50万以上"),
        SessionState(
            session_id="s1",
            turn_index=2,
            transcript=[
                {"role": "user", "content": "保额的保单", "request": first},
                {"role": "assistant", "content": "status=UNSUPPORTED", "extracted_output": {"message": "请补充金额"}},
            ],
            last_request=first,
        ),
    )
    assert second["trace_id"] == "s1-turn2"
    assert second["extra_input_params"]["policySearchParseArgs"]["query"] == "50万以上"
    assert second["extra_input_params"]["args"]["contexts"] == [
        {"role": "user", "content": "保额的保单", "sub_agent": ""},
        {"role": "assistant", "content": "请补充金额", "sub_agent": "POLICY_SEARCH"},
    ]


def test_deerflow_translator_inherits_thread_id() -> None:
    mock = load_adapter(load_project("deerflow")).mock()
    request = mock.request_from_user_message(
        UserMessage(type="text", text="继续"),
        SessionState(
            session_id="s1",
            turn_index=2,
            transcript=[
                {"role": "user", "content": "开始"},
                {"role": "assistant", "content": "ok", "extracted_output": {"session_summary": {"thread_id": "t-42"}}},
            ],
            last_request={"input": {"messages": []}, "config": {"configurable": {"thread_id": ""}}},
        ),
    )
    assert request == {
        "input": {"messages": [{"role": "user", "content": "继续"}]},
        "config": {"configurable": {"thread_id": "t-42"}},
    }
