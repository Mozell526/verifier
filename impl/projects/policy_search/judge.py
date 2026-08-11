"""Policy Search 的语义判定上下文。"""
from __future__ import annotations

from typing import Any, Dict

from impl.core.judge_protocol import ProjectJudge
from impl.core.schema import RunTrace


def _query_from_trace(trace: RunTrace) -> str:
    request = trace.normalized_request if isinstance(trace.normalized_request, dict) else {}
    extra = request.get("extra_input_params") or {}
    args = extra.get("policySearchParseArgs") or {}
    return str(args.get("query") or "")


def _intent_from_trace(trace: RunTrace) -> str:
    intent = trace.mock_intent
    if isinstance(intent, dict):
        return str(intent.get("user_intent") or "")
    return str(getattr(intent, "user_intent", "") or "")


class PolicySearchJudge(ProjectJudge):
    def build_context(self, trace: RunTrace) -> Dict[str, Any]:
        source_paths = {
            key: self.spec.source_path(key)
            for key in (
                "api_contract",
                "filter_contract",
                "technical_design",
                "business_config",
                "runtime_config",
                "golden_manifest",
            )
        }
        return {
            "project_type": "natural_language_to_policy_filter_tree",
            "user_intent": _intent_from_trace(trace) or _query_from_trace(trace),
            "application_boundary": trace.application_boundary or {},
            "system_prompt_extras": (
                "你评价的是保单筛选语义是否被完整、可执行且安全地表达。"
                "先判断服务依赖是否成功，再比较 query 与 filter。忽略 node_id 命名差异；"
                "允许逻辑等价的树。字段、操作符、值、角色、AND/OR/NOT 作用域、日期边界和条件完整性都必须正确。"
                "SUCCESS 必须有完整 filter；歧义、条件缺失或越界场景应 UNSUPPORTED 且不得返回部分 filter。"
                "业务实现、prompt 和配置是当前能力证据，不是不可质疑的自证。"
            ),
            "user_prompt_extras": {
                "query": _query_from_trace(trace),
                "actual_output": trace.extracted_output or {},
                "reference_contract": trace.reference_contract or {},
                "business_evidence_paths": source_paths,
                "evaluation_dimensions": [
                    "field_selection",
                    "operator_and_value",
                    "logical_scope",
                    "time_boundary",
                    "condition_completeness",
                    "safe_failure",
                ],
            },
        }

    def build_intent_frame(self, trace: RunTrace, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        query = _query_from_trace(trace)
        return {
            "project_id": self.spec.project_id,
            "downstream_consumer": "policy query execution service",
            "user_goal": _intent_from_trace(trace) or query,
            "request_candidates": [{"source": "policySearchParseArgs.query", "value": query}],
            "output_semantics": "an executable policy filter tree or an explicit safe UNSUPPORTED decision",
        }
