"""Stable DeerFlow ProjectMock implementation shared by Production and Draft."""
from __future__ import annotations

from typing import Any, Dict, Optional

from impl.core.mock_protocol import MultiTurnInteractiveMock, ProjectMock
from impl.core.schema import MockContinueDecision, MockIntentOutput, SingleTurnCase, MultiTurnCase


class DeerflowMockBase(MultiTurnInteractiveMock, ProjectMock):
    """Common multi-turn request behavior; role variants only refine extensions."""

    def build_user_intent(self, scenario: str):
        from impl.core.mock_agent import MockAgent, build_spec_from_project

        agent = MockAgent(self.spec)
        build_spec = build_spec_from_project(self.spec, scenario=scenario)
        return MockAgent.intent_output(agent.build_intent(build_spec))

    def build_next_request(
        self,
        intent,
        accumulated_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from impl.core.mock_agent import MockAgent

        agent = MockAgent(self.spec)
        acc = accumulated_output if isinstance(accumulated_output, dict) else {}
        turns = [turn for turn in (acc.get("turns") or []) if isinstance(turn, dict)]
        last_turn = turns[-1] if turns else {}
        # The in-flight protocol historically calls this ``extract_output``;
        # persisted Trace records use the canonical ``extracted_output``.
        # Accept both so Draft feedback remains useful across either boundary.
        last_output = next(
            (
                last_turn.get(name)
                for name in ("extracted_output", "extract_output")
                if isinstance(last_turn.get(name), dict)
            ),
            {},
        )
        live_feedback = {
            "stage": last_output.get("stage"),
            "missing_fields": last_output.get("missing_fields") or [],
            "extracted_output": last_output,
        }
        case_dict = {
            "scenario": str(getattr(intent, "scenario", "") or "intent_recognition"),
            "metadata": {
                "user_context": dict(getattr(intent, "user_context", {}) or {}),
                "next_turn_policy": self.next_turn_policy(),
            },
            "user_intent": str(getattr(intent, "user_intent", "") or ""),
        }
        query = str(agent.next_turn(case_dict, turns, live_feedback).get("query") or "")
        if not query:
            raise ValueError("MockAgent.next_turn 未生成下一轮 query")

        return {
            "input": {"messages": [{"role": "user", "content": query}]},
            "config": {
                "configurable": {
                    "thread_id": str(
                        (last_output.get("session_summary") or {}).get("thread_id")
                        or (
                            ((last_turn.get("live_request") or {}).get("config") or {}).get(
                                "configurable"
                            )
                            or {}
                        ).get("thread_id")
                        or ""
                    ),
                },
            },
        }

    def next_turn_policy(self) -> str:
        """Optional role-specific policy for dynamic user-language generation."""
        return ""

    def infer_user_intent(self, initial_request: Dict[str, Any]) -> MockIntentOutput:
        from impl.core.mock_agent import MockAgent

        return MockAgent(self.spec).infer_user_intent(
            initial_request,
            scenario="multi_turn_dimension_accumulation",
        )

    def decide_next_action(
        self,
        intent: MockIntentOutput,
        accumulated_output: Dict[str, Any],
    ) -> MockContinueDecision:
        from impl.core.mock_agent import MockAgent

        return MockAgent(self.spec).decide_next_action(intent, accumulated_output)

    def safety_max_turns(self) -> int:
        return 12

    def extract_mock_message(self, request: Dict[str, Any]) -> str:
        messages = (
            ((request.get("input") or {}).get("messages") or [])
            if isinstance(request, dict)
            else []
        )
        last = messages[-1] if messages and isinstance(messages[-1], dict) else {}
        return str(last.get("content") or "")

    def normalize_case(
        self,
        case: SingleTurnCase | MultiTurnCase,
    ) -> SingleTurnCase | MultiTurnCase:
        """Keep generated input schema-pure and leave runtime identity to Live."""
        case.input.pop("query", None)
        config = dict(case.input.get("config") or {})
        config["configurable"] = {}
        case.input["config"] = config
        if not case.scenario:
            case.scenario = str((case.metadata or {}).get("scenario") or "")
        if self.live_schema is not None and hasattr(self.live_schema, "check"):
            errors = self.live_schema.check.case_errors(
                {
                    "id": str(case.id or ""),
                    "input": dict(case.input or {}),
                    "output": case.output,
                    "reference": case.reference,
                    "scenario": case.scenario,
                }
            )
            case.metadata["schema_ok"] = not errors
            if errors:
                case.metadata["schema_errors"] = errors
            else:
                case.metadata.pop("schema_errors", None)
        return case
