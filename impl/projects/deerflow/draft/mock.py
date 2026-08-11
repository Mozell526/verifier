"""Candidate DeerFlow Mock grounded in its mandatory investigation contract."""
from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from impl.projects.deerflow.mock_base import DeerflowMockBase


class DeerflowMockDraft(DeerflowMockBase):
    """Generate concrete members of the broad DeerFlow business-user population."""

    @staticmethod
    def _contract() -> dict[str, Any]:
        path = (
            Path(__file__).resolve().parent
            / "investigation"
            / "mock"
            / "docs"
            / "mock-investigation-contract.json"
        )
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(f"DeerFlow Mock investigation contract must be an object: {path}")
        return raw

    def scenarios(self) -> list[str]:
        """Ordinary pools sample open-world users; directed scenarios remain callable."""
        return ["open_world_user"]

    @staticmethod
    def _select_demand_space(
        contract: dict[str, Any], scenario: str, *, requested_intent: str = ""
    ) -> dict[str, Any]:
        spaces = list(contract.get("demand_spaces") or [])
        scenario_name = str(scenario or "").strip().lower()
        if scenario_name in {"authorization_boundary", "non_agent_intent", "service_unavailable"}:
            preferred = "authorization-or-domain-boundary"
        elif scenario_name == "clarification":
            preferred = "clarification-and-ambiguity"
        elif scenario_name == "multi_turn_dimension_accumulation":
            preferred = "continue-or-adjust-existing-work"
        elif requested_intent and any(
            token in requested_intent for token in ("继续", "已有", "调整", "修改", "增加")
        ):
            preferred = "continue-or-adjust-existing-work"
        else:
            preferred = "open-world-nbev-work"
        selected = next(
            (item for item in spaces if item.get("space_id") == preferred),
            spaces[0] if spaces else {},
        )
        if not selected:
            raise ValueError("DeerFlow Mock investigation contract has no demand spaces")
        return selected

    @staticmethod
    def _population_sample() -> dict[str, str]:
        return {
            "business_familiarity": secrets.choice(
                ("new_to_the_work", "working_familiarity", "deep_experience")
            ),
            "tool_familiarity": secrets.choice(
                ("first_use", "occasional_use", "habitual_use")
            ),
            "expression": secrets.choice(
                (
                    "brief_and_elliptical",
                    "context_rich",
                    "uncertain",
                    "corrective",
                    "direct",
                )
            ),
            "current_state": secrets.choice(
                ("starting", "continuing", "checking", "comparing", "reconsidering")
            ),
        }

    def build_user_intent(self, scenario: str):
        return self.build_user_intent_for_case(scenario)

    def build_user_intent_for_case(
        self,
        scenario: str,
        *,
        requested_intent: str = "",
        template: dict | None = None,
    ):
        from impl.core.mock_agent import MockAgent, build_spec_from_project

        requested = str(requested_intent or "").strip()
        contract = self._contract()
        selected = self._select_demand_space(
            contract, scenario, requested_intent=requested
        )
        build_spec = build_spec_from_project(self.spec, scenario=scenario)
        build_spec.requested_intent = requested
        build_spec.template = {
            "generation_mode": (
                "constrained_user_expression"
                if requested
                else "open_world_user_population"
            ),
            "contract_mode": "deerflow_mock_investigation",
            "single_pass": True,
            "diversity_seed": secrets.token_hex(12),
            "population_sample": self._population_sample() if not requested else {},
            "business_values": contract.get("business_values") or [],
            "evaluation_dimensions": (
                (contract.get("evaluation_scope") or {}).get("dimensions") or []
            ),
            "selected_demand_space": selected,
            "generation_constraints": [
                "先形成当前用户的具体工作处境，再产生 user_context、user_intent 和 query",
                "沿 variation_space 改变事实与表达，满足 evaluation_coverage 和 validity_constraints",
                "固定用户目标存在时只做自然表达，不新增月份、金额、机构、人物、视角或历史对话",
                "用户原话不得出现实现、接口、机器标识、测试或评估术语",
                "不得把调查示例、历史样本或定向场景名当成封闭意图菜单",
            ],
            **dict(template or {}),
        }
        return MockAgent.intent_output(MockAgent(self.spec).build_intent(build_spec))

    def build_initial_request(self, intent):
        """Map user language to DeerFlow's request schema without another LLM."""
        query = str(getattr(intent, "query", "") or "").strip()
        if not query:
            raise ValueError("DeerFlow Draft Mock generated an empty user query")
        return {
            "input": {"messages": [{"role": "user", "content": query}]},
            "config": {"configurable": {}},
        }

    def next_turn_policy(self) -> str:
        return (
            "只围绕用户目标、已有对话和上一轮可见业务结果自然推进。"
            "保持普通业务用户的表达方式，保留尚未确定的信息，不替用户补造新的事实。"
            "上一轮只完成部分目标时，继续追问或补充合适的业务视角；"
            "用户未选择的视角不要强行加入。"
        )
