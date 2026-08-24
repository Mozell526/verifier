"""Judge execution strategy seam.

The default strategy is deliberately the historical single-pass Production
Judge. Candidate Roles may provide another strategy, but the Core does not
know its business stages or schemas.
"""
from __future__ import annotations

from typing import Optional, Protocol, TYPE_CHECKING

from impl.core.schema import JudgeResult, RunTrace

if TYPE_CHECKING:
    from impl.core.judge_protocol import ProjectJudge


class JudgeExecution(Protocol):
    def run(
        self,
        judge: "ProjectJudge",
        trace: RunTrace,
        user_intent: Optional[str],
    ) -> JudgeResult:
        ...


class SinglePassJudgeExecution:
    """Historical Production execution: one context build and one Judge call."""

    def run(
        self,
        judge: "ProjectJudge",
        trace: RunTrace,
        user_intent: Optional[str],
    ) -> JudgeResult:
        from impl.core.judge import build_judge_evidence_view

        context = judge.build_context(trace)
        context = {
            **(context or {}),
            "judge_evidence": build_judge_evidence_view(trace),
        }
        context["intent_frame"] = judge.build_intent_frame(trace, context)
        judge._last_judge_context = context
        return judge._run_llm_judge(trace, context, user_intent)
