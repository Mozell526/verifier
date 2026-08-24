"""Policy Search 首版归因上下文。"""
from __future__ import annotations

from typing import Any, Dict

from impl.core.attribute_protocol import ProjectAttribute
from impl.core.schema import JudgeResult, RunTrace


class PolicySearchAttribute(ProjectAttribute):
    def build_context(self, trace: RunTrace, judge_result: JudgeResult) -> Dict[str, Any]:
        return {
            "system_prompt_extras": (
                "只在 judge 已有当前 case 的 expected/actual 证据时归因。"
                "按 request construction、HTTP delivery、output extraction、规则/配置召回、"
                "LLM fallback、filter validation 与 safe-failure 顺序定位；不要把外部服务不可用归成语义算法错误。"
            ),
            "user_prompt_extras": {
                "business_source": self.spec.source_repository,
                "business_config": self.spec.source_path("business_config"),
                "runtime_config": self.spec.source_path("runtime_config"),
                "technical_design": self.spec.source_path("technical_design"),
                "actual_output": trace.extracted_output or {},
                "judge_expected": judge_result.expected or {},
                "judge_wrong": list(judge_result.wrong or []),
                "judge_missing": list(judge_result.missing or []),
                "application_boundary": trace.application_boundary or {},
            },
            "chain_nodes_to_check": [
                "request_construction",
                "http_delivery",
                "output_extraction",
                "deterministic_rules_and_config",
                "llm_fallback",
                "filter_validation",
            ],
        }
