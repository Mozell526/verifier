"""Policy Search 单轮用户模拟。"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from impl.core.mock_protocol import ProjectMock, SingleTurnMock
from impl.core.schema import MockIntentOutput
from impl.projects.policy_search.rich_mock import MockDemand


SCENARIO_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "atomic_condition": {
        "intent": "筛选保额不少于五十万元的保单",
        "query": "保额不低于50万的保单",
    },
    "compound_logic": {
        "intent": "筛选张三或李四作为投保人、今年生效且保额不少于五十万元的保单",
        "query": "张三或李四作为投保人，今年生效且保额不低于50万的保单",
    },
    "time_boundary": {
        "intent": "筛选八月份生效的保单",
        "query": "8月生效的保单",
    },
    "enum_alias": {
        "intent": "筛选万能险类别的保单",
        "query": "万能帐户保单",
    },
    "agent_identity": {
        "intent": "筛选由当前登录代理人销售的保单",
        "query": "我销售的保单",
    },
    "context_disambiguation": {
        "intent": "沿用上一轮张三投保人的条件并进一步限定今年生效",
        "query": "那今年生效的呢",
        "contexts": [
            {"role": "user", "content": "查张三作为投保人的保单", "sub_agent": ""},
            {"role": "assistant", "content": "已为你查询张三作为投保人的保单。", "sub_agent": "POLICY_SEARCH"},
        ],
    },
    "clarification": {
        "intent": "表达了年缴保费筛选方向但没有提供必要金额条件",
        "query": "年缴保费的保单",
    },
    "unsupported": {
        "intent": "筛选投诉次数超过三次但首期不支持的保单",
        "query": "投诉超过3次的保单",
    },
    "surface_generalization": {
        "intent": "用口语表达筛选处于失效状态的保单",
        "query": "帮我找下已经失效了的那些保单",
    },
}


class PolicySearchMock(SingleTurnMock, ProjectMock):
    def build_user_intent_for_case(
        self,
        scenario: str,
        *,
        requested_intent: str = "",
        template: Dict[str, Any] | None = None,
    ) -> MockIntentOutput:
        """消费覆盖规划器给出的事实任务，不让 LLM 补造测试答案。"""
        task = dict(template or {})
        if "mock_query" not in task:
            return super().build_user_intent_for_case(
                scenario,
                requested_intent=requested_intent,
                template=template,
            )
        return MockIntentOutput(
            user_intent=str(requested_intent or task.get("user_intent") or ""),
            query=str(task.get("mock_query") or ""),
            user_context={"contexts": list(task.get("contexts") or [])},
            system_understanding="用户通过自然语言筛选保单，系统返回查询语法树而非保单列表。",
            scenario=scenario,
        )

    def generate_demand_case(self, demand: MockDemand):
        """通过公共 Mock 模板方法生成一条覆盖任务对应的标准 Case。"""
        return self.generate_mock_case(
            scenario=demand.scenario,
            intent=demand.user_intent,
            template={
                "mock_query": demand.query,
                "contexts": list(demand.contexts),
            },
        )

    def build_user_intent(self, scenario: str) -> MockIntentOutput:
        example = SCENARIO_EXAMPLES.get(scenario) or SCENARIO_EXAMPLES["atomic_condition"]
        return MockIntentOutput(
            user_intent=str(example["intent"]),
            query=str(example["query"]),
            user_context={"contexts": list(example.get("contexts") or [])},
            system_understanding="用户通过自然语言筛选保单，系统返回查询语法树而非保单列表。",
            scenario=scenario or "atomic_condition",
        )

    def build_initial_request(self, intent: MockIntentOutput) -> Dict[str, Any]:
        contexts = list((intent.user_context or {}).get("contexts") or [])
        request_id = uuid.uuid4().hex
        return {
            "session_id": f"verifier-policy-{request_id[:12]}",
            "trace_id": f"verifier-policy-{request_id}",
            "user_id": "verifier-user",
            "org_id": "verifier-org",
            "org_name": "verifier",
            "ts": 1785983400000,
            "token": "",
            "app_scenario": "policy_search_parse",
            "source": "verifier",
            "user_text": "",
            "history": [],
            "user_action": "write",
            "action_scenario": "policySearch",
            "extra_input_params": {
                "policySearchParseArgs": {
                    "query": intent.query,
                    "currentTime": "2026-08-06 10:30:00",
                    "agentCode": "A12345678",
                },
                "agent_args": None,
                "args": {"contexts": contexts},
            },
            "application_setting": None,
            "scenario": None,
        }

    def extract_mock_message(self, request: Dict[str, Any]) -> str:
        extra = request.get("extra_input_params") or {}
        args = extra.get("policySearchParseArgs") or {}
        return str(args.get("query") or "")
