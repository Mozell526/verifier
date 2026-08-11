"""authority.resolve 的 ToolGateway 包装（VerifiableTool + audit 收集）。

ToolGateway Port（authority.md §4.2）：执行动态获取能力，结果自动回填物化；
一次调用 = 绑定 Environment 的一次 Agent 会话。调用结果与
`environment_snapshot_sha256` 一起写入 audit，供 Core 后处理（authority_gate）
与审计复用；audit 归属当前调用方 trace，不跨 trace 复用。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Mapping

from impl.core.authority_environment import (
    AuthorityEnvironment,
    AuthorityToolProtocolViolation,
    resolve_authority,
)
from impl.core.schema import AuthorityClaim, AuthorityRequest, AuthorityResolution
from impl.tools import VerifiableTool

TOOL_ID = "authority.resolve"

# authority-minimal-chain.md §8：模型未能完成查证（工具导航违例、工具预算耗尽）是
# 确定性执行失败，不是端点瞬时故障。这类失败不落 tool_failure，而是归一成
# unresolved/gap_only（依据不充分）+ 缺料清单，使 fulfilled.md §10 依据链可回溯；
# 端点故障与未知错误仍走 tool_failure fail-closed。
_VERIFICATION_FAILURE_MARKERS = (
    "tool_budget_exceeded",
    "budget exceeded",
    "tool budget",
)


def _looks_like_verification_failure(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _VERIFICATION_FAILURE_MARKERS)


def _verification_failure_resolution(
    *, claim_mode: bool, error: str
) -> "AuthorityResolution":
    return AuthorityResolution(
        status="gap_only" if claim_mode else "unresolved",
        statement="",
        reason=(
            f"authority 未能完成查证（{error}），无法产出裁决。"
            "需能支撑裁决的职责/能力边界资料（业务方确认的 normative_rule / "
            "external_fact，或已登记的 inlive_boundary 边界声明）与完整可回溯的 "
            "Search→Load 查证记录；不得以 current_behavior 充当裁决依据。"
        ),
        basis_evidence_ref_ids=(),
        required_evidence=(
            "业务方确认的职责/能力边界声明（normative_rule / external_fact / 已登记 "
            "inlive_boundary 声明），以及本次未能完成的 Search→Load 查证记录",
        ),
    )


class AuthorityTool:
    """把 resolve 包装为 Judge 可调用的 VerifiableTool，并收集 Tool audit。"""

    def __init__(self, env: AuthorityEnvironment, *, llm: Any = None):
        self._env = env
        self._llm = llm
        self.audit: dict[str, Mapping[str, Any]] = {}
        # authority.md §10：相同完整问题 + Environment snapshot + Evidence revisions
        # 在一次 Runtime 任务内不得重复调用。cache 归属单次 judge 会话（每次
        # _build_core_context 新建），重复问题直接复用同一 resolution 与 tool_call_id。
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}

    def _execute(self, decision_question: str, claim: Mapping[str, Any] | None = None) -> dict[str, Any]:
        question = str(decision_question or "").strip()
        if not question:
            raise ValueError("authority.resolve requires a non-empty decision_question")
        normalized_claim = None
        if claim is not None:
            if not isinstance(claim, Mapping):
                raise ValueError("authority.resolve claim must be an object")
            normalized_claim = {
                "claim_statement": str(claim.get("claim_statement") or "").strip(),
                "subject": claim.get("subject"),
                "conclusion_kind": str(claim.get("conclusion_kind") or "").strip(),
                "intended_use": str(claim.get("intended_use") or "").strip(),
            }
        claim_key = json.dumps(normalized_claim, ensure_ascii=False, sort_keys=True, default=str)
        cache_key = (question + "\x00" + claim_key, self._env.environment_snapshot_sha256)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return dict(cached)
        # 一次 authority.resolve 调用是一次独立的证据 run：basis 校验与
        # claim 比对的 context_coverage 只能看到本次调用自己 Search/Load 的
        # 痕迹，不能继承同一 judge 会话内先前调用的候选/Load 记录。
        # 真实 AuthorityEnvironment 恒有 context_run；无 run 的宿主桩跳过重置。
        run = getattr(self._env, "context_run", None)
        if run is not None:
            run.reset_trace()
        call_id = f"authority.{self._env.project_id}.{uuid.uuid4().hex[:12]}"
        request_payload = {"decision_question": question}
        if normalized_claim is not None:
            request_payload["claim"] = normalized_claim
        try:
            resolution = resolve_authority(
                self._env,
                AuthorityRequest(
                    question,
                    claim=(AuthorityClaim(**normalized_claim) if normalized_claim is not None else None),
                ),
                llm=self._llm,
                authority_call_id=call_id,
            )
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, AuthorityToolProtocolViolation) or _looks_like_verification_failure(error):
                resolution = _verification_failure_resolution(
                    claim_mode=normalized_claim is not None,
                    error=error,
                )
                self.audit[call_id] = {
                    "request": request_payload,
                    "resolution": resolution,
                    "independent_resolution": None,
                    "environment_snapshot_sha256": self._env.environment_snapshot_sha256,
                }
                result = {
                    "tool_call_id": call_id,
                    "status": resolution.status,
                    "statement": "",
                    "reason": resolution.reason,
                    "basis_evidence_ref_ids": [],
                    "required_evidence": list(resolution.required_evidence),
                }
                self._cache[cache_key] = result
                return dict(result)
            self.audit[call_id] = {
                "request": request_payload,
                "tool_failure": True,
                "error": error,
                "environment_snapshot_sha256": self._env.environment_snapshot_sha256,
            }
            result = {
                "tool_call_id": call_id,
                "status": "tool_failure",
                "statement": "",
                "reason": f"Authority 能力不可用（执行失败）：{error}",
                "basis_evidence_ref_ids": [],
                "required_evidence": [],
            }
            self._cache[cache_key] = result
            return dict(result)
        self.audit[call_id] = {
            "request": request_payload,
            "resolution": resolution,
            "independent_resolution": resolution.independent_resolution,
            "environment_snapshot_sha256": self._env.environment_snapshot_sha256,
        }
        result = {
            "tool_call_id": call_id,
            "status": resolution.status,
            "statement": resolution.statement,
            "reason": resolution.reason,
            "basis_evidence_ref_ids": list(resolution.basis_evidence_ref_ids),
            "required_evidence": list(resolution.required_evidence),
        }
        self._cache[cache_key] = result
        return dict(result)

    def as_verifiable_tool(self) -> VerifiableTool:
        def execute(decision_question: str, claim: Mapping[str, Any] | None = None) -> dict[str, Any]:
            # 包装为普通函数：build_agno_tools 需要可设置 __name__ 的 callable。
            return self._execute(decision_question, claim)

        return VerifiableTool(
            tool_id=TOOL_ID,
            description=(
                "确定一个完整业务规则、定义、契约或来源选择问题的可靠结论。"
                "在两类情况下调用：(1) 当前判断确实遇到标准冲突、且无法用已有证据"
                "直接裁决；(2) 当前评价依赖“产品是否具备某项能力、某事项是否属于"
                "产品职责”的能力/职责边界裁决（如某查询维度是否属于产品可支持范围）。"
                "能力/职责边界问题按模板提问：「<产品/模块> 是否支持 <用户要的能力>？"
                "或 <事项> 是否属于 <产品> 职责？」（例：客户搜索产品是否支持按车牌查询？"
                "住院医疗保险是否属于客户搜索产品可查询的险种范围？），不得把 live 输出、"
                "reference 或 Judge 期望写进问题。"
                "一次只提交一个短且自包含的业务条件问题。工具参数必须是严格 JSON；"
                "decision_question/claim_statement 内如需引用原话，使用中文引号或正确转义英文双引号。"
                "question-only 模式返回 resolved/unresolved；带 claim 模式返回 "
                "supported/contradicted/ungoverned/gap_only，并给出依据与待补证据。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "decision_question": {
                        "type": "string",
                        "description": (
                            "需要确定的一个完整业务规则、定义、契约或来源选择问题；"
                            "必须包含所有可能改变答案的业务条件（版本、渠道、场景等）。"
                        ),
                    },
                    "claim": {
                        "type": "object",
                        "description": "可选：Judge 需要 Authority 担保的规范性断言；必须是结论陈述，不是引导性问题。",
                        "properties": {
                            "claim_statement": {"type": "string"},
                            "subject": {"description": "项目自定义业务主题锚点"},
                            "conclusion_kind": {"type": "string"},
                            "intended_use": {"type": "string"},
                        },
                        "required": ["claim_statement", "subject", "conclusion_kind", "intended_use"],
                        "additionalProperties": False,
                    },
                },
                "required": ["decision_question"],
                "additionalProperties": False,
            },
            execute_fn=execute,
        )


def build_authority_resolve_tool(
    env: AuthorityEnvironment, *, llm: Any = None
) -> AuthorityTool:
    return AuthorityTool(env, llm=llm)
