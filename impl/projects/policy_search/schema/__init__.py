"""Policy Search 的真实 API 请求与归一输出 schema。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContextItem:
    role: str
    content: str
    sub_agent: str = ""


@dataclass
class ConversationArgs:
    contexts: List[ContextItem]


@dataclass
class PolicySearchParseArgs:
    query: str
    currentTime: str
    agentCode: str


@dataclass
class PolicySearchExtraInputParams:
    policySearchParseArgs: PolicySearchParseArgs
    args: ConversationArgs
    agent_args: Optional[Dict[str, Any]] = None


@dataclass
class PolicySearchRequest:
    """POST /api/v1/policy-search/parse 的 AskBob 请求信封。"""

    session_id: str
    trace_id: str
    extra_input_params: PolicySearchExtraInputParams
    user_id: str = ""
    org_id: str = ""
    org_name: str = ""
    ts: Any = ""
    token: str = ""
    app_scenario: str = "policy_search_parse"
    source: str = "verifier"
    user_text: str = ""
    history: List[Any] = field(default_factory=list)
    user_action: str = "write"
    action_scenario: str = "policySearch"
    application_setting: Optional[Dict[str, Any]] = None
    scenario: Any = None


@dataclass
class PolicySearchExtractOutput:
    """从业务响应中提取的稳定判定形状。"""

    code: int
    msg: str
    status: str
    query: str
    filter: Optional[Dict[str, Any]]
    message: str
