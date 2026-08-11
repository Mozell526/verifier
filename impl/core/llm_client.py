from __future__ import annotations

import inspect
from types import MethodType
import json
import re
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import json_repair
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from .llm_router import LlmEndpoint, LlmRouter
from openai import Omit, OpenAI

from .config import get_llm_config
from .config_schema import ConfigError, openai_compatible_base_url

if TYPE_CHECKING:
    from .structured_output import StructuredOutputSpec

# Session start timestamp: ensures sessions from different runs don't share context
SESSION_START_TIME = int(time.time())
_USE_CONFIG = object()
_ROUTER_REGISTRY_LOCK = threading.Lock()
_ROUTER_REGISTRY: dict[tuple[tuple[str, str, str, str], ...], LlmRouter] = {}


def _parse_tool_calls_with_aliases(self, tool_calls_data):
    parsed = OpenAILike.parse_tool_calls(self, tool_calls_data)
    aliases = getattr(self, "logical_tool_aliases", {})
    for call in parsed:
        function = call.get("function") if isinstance(call, dict) else None
        if isinstance(function, dict) and function.get("name") in aliases:
            function["name"] = aliases[function["name"]]
    return parsed


def _json_context_tools(tools: List[Any]) -> List[Any]:
    """Wrap tool entrypoints so tool results enter the model context as JSON text.

    Agno stringifies non-string tool returns with str(), which leaks Python repr
    (single quotes, True/False/None) into the model context. Wrapping at the LLM
    boundary keeps the model view byte-identical to the audit log, and leaves the
    tool layer's structured return contract intact for programmatic consumers.
    """
    from agno.tools import Function
    from ..tools.protocol import json_tool

    wrapped: List[Any] = []
    for tool in tools or []:
        if isinstance(tool, Function):
            copy = tool.model_copy(deep=False)
            if copy.entrypoint is not None:
                copy.entrypoint = json_tool(copy.entrypoint)
            wrapped.append(copy)
        elif callable(tool):
            wrapped.append(json_tool(tool))
        else:
            wrapped.append(tool)
    return wrapped


def _supported_agent_kwargs(factory: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Only pass optional Agent settings supported by the installed Agno."""
    try:
        parameters = inspect.signature(factory).parameters
    except (TypeError, ValueError):
        return kwargs
    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in parameters}


class JsonExtractionError(ValueError):
    """Raised when an LLM response cannot be parsed into a JSON value."""


def _json_error_summary(exc: json.JSONDecodeError) -> str:
    return f"{exc.msg} at line {exc.lineno} column {exc.colno} (char {exc.pos})"


def extract_json(text: str) -> Any:
    text = text.strip()
    if not text:
        return {}
    parse_errors: list[str] = []
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        parse_errors.append(f"whole response: {_json_error_summary(exc)}")
    # Try every fenced block in order. Many LLM outputs embed non-JSON
    # snippets (yaml configs, regex examples) inside ``` fences BEFORE the
    # actual JSON block — a non-greedy single match would silently grab the
    # first fence and drop the real JSON. Prefer json-tagged fences, then
    # any fence, then a bare-object fallback.
    fence_matches = list(re.finditer(r"```(\w+)?\s*(.*?)```", text, re.S))
    json_tagged = [m for m in fence_matches if (m.group(1) or "").lower() == "json"]
    untagged = [m for m in fence_matches if (m.group(1) or "").lower() not in {"json", ""}]
    any_tagged = fence_matches
    for group_name, group in (("json fenced block", json_tagged), ("non-json fenced block", untagged), ("any fenced block", any_tagged)):
        for m in group:
            body = m.group(2)
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                parse_errors.append(f"{group_name}: {_json_error_summary(exc)}")
                continue
    start = min([idx for idx in [text.find("{"), text.find("[")] if idx >= 0], default=-1)
    if start >= 0:
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError as exc:
            parse_errors.append(f"bare JSON from first bracket: {_json_error_summary(exc)}")
    try:
        return json_repair.repair_json(text, return_objects=True)
    except Exception as exc:
        parse_errors.append(f"json_repair: {type(exc).__name__}: {exc}")
    preview = text[:500]
    detail = "; ".join(parse_errors[-4:]) if parse_errors else "no JSON object or array found"
    raise JsonExtractionError(
        "LLM 输出不是合法 JSON，且标准 JSON repair 未能修复，无法进入结构化校验。"
        f"解析错误：{detail}\n原始输出预览：{preview}"
    )


def _exact_json_objects(text: str) -> list[Dict[str, Any]]:
    """Return verbatim JSON objects embedded in a mixed model response."""
    decoder = json.JSONDecoder()
    objects: list[Dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, consumed = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        span = (start, start + consumed)
        if span in seen:
            continue
        seen.add(span)
        objects.append(value)
    return objects


def _select_schema_matching_object(
    text: str,
    parsed: Any,
    output_spec: "StructuredOutputSpec",
) -> Any:
    """Prefer an exact embedded object only when it already passes the spec.

    This does not repair or mutate a candidate. It only prevents unrelated
    leading prose/tool facts such as ``[10, 14]`` from becoming the top-level
    value when the response also contains the requested valid JSON object.
    """
    from .schema_validator import SchemaValidator

    validator = SchemaValidator(output_spec)
    if validator.is_valid(parsed, strict=True, allow_extra=False):
        return parsed
    for candidate in _exact_json_objects(text):
        if validator.is_valid(candidate, strict=True, allow_extra=False):
            return candidate
    return parsed


def _response_content(result: Any) -> str:
    content = getattr(result, "content", result)
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    return str(content or "")


def _run_status(result: Any) -> str:
    status = getattr(result, "status", None)
    return str(getattr(status, "value", status) or "").strip().upper()


def _run_failed(result: Any) -> bool:
    return _run_status(result) in {"ERROR", "CANCELLED"}


def _raw_response(result: Any) -> Any:
    raw = getattr(result, "raw_response", None)
    if raw is not None:
        return raw
    if hasattr(result, "model_dump"):
        try:
            dump = result.model_dump()
            # Preserve metrics if available
            if hasattr(result, "metrics") and "metrics" not in dump:
                metrics = getattr(result, "metrics")
                if hasattr(metrics, "model_dump"):
                    dump["metrics"] = metrics.model_dump()
                elif isinstance(metrics, dict):
                    dump["metrics"] = metrics
            return dump
        except Exception:
            pass
    if hasattr(result, "to_dict"):
        try:
            dump = result.to_dict()
            if isinstance(dump, dict):
                # RunOutput can contain the entire prompt/message history.  Only keep
                # provider/run diagnostics here; ContextStore already records messages.
                return {
                    key: dump[key]
                    for key in ("content", "status", "model", "model_provider", "model_provider_data", "events", "metrics")
                    if key in dump and dump[key] not in (None, "", [], {})
                }
        except Exception:
            pass
    if isinstance(result, dict):
        return result
    response = {"content": _response_content(result)}
    # Try to extract metrics from Agno RunOutput
    if hasattr(result, "metrics"):
        metrics = getattr(result, "metrics")
        if hasattr(metrics, "model_dump"):
            response["metrics"] = metrics.model_dump()
        elif isinstance(metrics, dict):
            response["metrics"] = metrics
    return response


def chat_completions_url(base_url: str) -> str:
    """Build the raw Chat Completions endpoint from a validated API root."""
    root = openai_compatible_base_url(base_url, "llm.base_url")
    return f"{root}/chat/completions"


def _extract_tool_call_log(result: Any) -> list:
    """
    Extract tool-call records from an Agno RunResponse.

    Agno stores the conversation as `result.messages`, a list of Message objects.
    Each assistant Message may carry `.tool_calls` (a list of ToolCall objects with
    .function.name / .function.arguments). Each tool Message carries `.tool_call_id`
    and `.content` (the tool's return value). We pair them by tool_call_id.

    The function is defensive: it handles pydantic Messages, dict-shaped messages,
    and missing attributes, returning [] when nothing is found.
    """
    logs: list = []

    # 1. Locate the messages list on the result object.
    messages = getattr(result, "messages", None)
    if not messages:
        # Some Agno versions nest under run_response / raw_response
        for attr in ("run_response", "raw_response"):
            inner = getattr(result, attr, None)
            if inner is not None:
                messages = getattr(inner, "messages", None)
                if messages:
                    break
    if not messages:
        return []

    # 2. Build a tool_call_id -> tool_result map from tool messages.
    tool_results: Dict[str, Any] = {}
    for msg in messages:
        # Normalize to dict once for cheap attribute access.
        try:
            md = msg.model_dump() if hasattr(msg, "model_dump") else (
                msg if isinstance(msg, dict) else None
            )
        except Exception:
            md = None
        role = (md or {}).get("role") if isinstance(md, dict) else getattr(msg, "role", None)
        if role != "tool":
            continue
        tcid = (md or {}).get("tool_call_id") if isinstance(md, dict) else getattr(msg, "tool_call_id", None)
        if not tcid:
            continue
        content = (md or {}).get("content") if isinstance(md, dict) else getattr(msg, "content", None)
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False)
        tool_results[tcid] = content

    # 3. Walk assistant messages, emit one log entry per tool_call.
    for msg in messages:
        try:
            md = msg.model_dump() if hasattr(msg, "model_dump") else (
                msg if isinstance(msg, dict) else None
            )
        except Exception:
            md = None
        role = (md or {}).get("role") if isinstance(md, dict) else getattr(msg, "role", None)
        if role != "assistant":
            continue
        tool_calls = (md or {}).get("tool_calls") if isinstance(md, dict) else getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue
        for tc in tool_calls:
            # tc may be a pydantic ToolCall or a dict.
            tcd = tc.model_dump() if hasattr(tc, "model_dump") else (
                tc if isinstance(tc, dict) else None
            )
            if not isinstance(tcd, dict):
                continue
            fn = tcd.get("function") or {}
            name = fn.get("name") or tcd.get("name") or ""
            args = fn.get("arguments") or tcd.get("arguments")
            tcid = tcd.get("id") or tcd.get("tool_call_id") or ""
            # arguments may arrive as a JSON string; parse it for readability.
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            entry = {
                "tool_name": name,
                "tool_call_id": tcid,
                "arguments": args,
                "result": tool_results.get(tcid),
            }
            logs.append(entry)
    return logs


def _tool_budget_error(tool_call_log: list, limit: Optional[int]) -> Optional[str]:
    """Return a deterministic protocol error when an SDK run exceeds its budget."""
    if limit is None or len(tool_call_log) <= int(limit):
        return None
    return (
        f"actual tool calls {len(tool_call_log)} exceed configured limit {int(limit)}"
    )


def _extract_messages(result: Any) -> List[Dict[str, Any]]:
    """从 Agno RunResponse 提取 OpenAI messages 协议的完整消息列表。

    供 context_store 记录实际 LLM 调用的输入输出。每个消息 {role, content, ...}，
    role 不限定 system/user/assistant/tool——按 agno 实际返回的原样保留。
    """
    messages = getattr(result, "messages", None)
    if not messages:
        for attr in ("run_response", "raw_response"):
            inner = getattr(result, attr, None)
            if inner is not None:
                messages = getattr(inner, "messages", None)
                if messages:
                    break
    if not messages:
        return []
    out: List[Dict[str, Any]] = []
    for msg in messages:
        try:
            md = msg.model_dump() if hasattr(msg, "model_dump") else (
                msg if isinstance(msg, dict) else None
            )
        except Exception:
            md = None
        if isinstance(md, dict):
            out.append(md)
        else:
            # 退化兜底：直接按属性取
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", None)
            if role is not None or content is not None:
                out.append({"role": role, "content": content})
    return out


def _track_context(self: "LlmClient", system: str, user: str, result: Any,
                   trace_id: str, token_metrics: Dict[str, Any],
                   elapsed_ms: int, error: Optional[str],
                   *, runtime: Optional[Dict[str, Any]] = None) -> None:
    """把本次 LLM 调用的实际 messages 上传到 context_store，供 context.html 检索。

    只做记录，不阻断主流程；任何异常都吞掉。
    """
    try:
        from .context_store import save_context
        from .schema.context import ContextRecord
        messages = _extract_messages(result)
        if not messages:
            # result 为 None（调用失败）时，至少把 system/user 请求记下来
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        response: Dict[str, Any] = {}
        content = _response_content(result) if result is not None else ""
        if content:
            response["content"] = content
        if token_metrics:
            response["metrics"] = token_metrics
        if runtime:
            response["runtime"] = runtime
        if error and result is not None:
            response["raw_response"] = _raw_response(result)
        prompt_size = sum(len(str(m.get("content") or "")) for m in messages)
        runtime_model = str((runtime or {}).get("selected_model") or "")
        if not runtime_model:
            attempts = list((runtime or {}).get("attempts") or [])
            if attempts:
                runtime_model = str(attempts[-1].get("model") or "")
        record = ContextRecord(
            record_id=str(uuid.uuid4()),
            trace_id=str(trace_id or ""),
            project_id=str(getattr(self, "_project_id", "") or ""),
            caller=str(getattr(self, "_caller", "") or "llm"),
            messages=messages,
            response=response or None,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            prompt_size=int(prompt_size),
            llm_model=runtime_model or str(self.model or ""),
            elapsed_ms=int(elapsed_ms),
            error=error,
            governance=dict(getattr(self, "_context_governance_report", {}) or {}),
        )
        save_context(record)
    except Exception:
        pass


def project_llm_client(spec: Any, role: str, knowledge: Any = None, tools: list = None,
                       tool_call_limit: Optional[int] = None,
                       compress_tool_results: bool = False,
                       max_tool_calls_from_history: Optional[int] = None) -> "LlmClient":
    """
    Create LLM client for judge/attribute with NO persistence, NO memories, NO sessions.

    Context engineering strategy:
    - Knowledge: NO - use tools for on-demand retrieval
    - User memories: NO - each case should be independent
    - Session history: NO - each judge call is stateless
    - DB persistence: NO - no session/memory storage
    - Tool call budget: only set for roles that actually use tools (attribute).

    Args:
        spec: Project specification
        role: Role name (e.g., "judge", "attribute")
        knowledge: Optional knowledge base (DEPRECATED - use tools instead)
        tools: Optional list of tools to provide to the agent
        tool_call_limit: Cap on tool calls within one agent.run()
        compress_tool_results: If True, compress prior tool results
        max_tool_calls_from_history: Prune tool messages from history
    """
    project_id = str(getattr(spec, "project_id", "default") or "default")
    # CRITICAL: Do NOT create JsonDb or MemoryManager
    # CRITICAL: Do NOT set user_id - it triggers Agno to auto-create impl/knowledge/{user_id}/ directory
    client = LlmClient(
        role=role,
        memory_db=None,  # NO persistence
        memory_manager=None,  # NO memories
        knowledge=knowledge,  # Will be set to None by caller
        knowledge_retriever=None,
        tools=tools,
        user_id=None,  # CRITICAL: None to prevent auto directory creation
        session_id=None,  # NO session persistence
        tool_call_limit=tool_call_limit,
        compress_tool_results=compress_tool_results,
        max_tool_calls_from_history=max_tool_calls_from_history,
    )
    client._project_id = project_id
    client._caller = role
    return client


class LlmClient:
    def __init__(
        self,
        role: str = "",
        config: Any = None,
        memory_manager: Any = None,
        memory_db: Any = None,
        knowledge: Any = None,
        knowledge_retriever: Any = None,
        tools: list = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_call_limit: Optional[int] = None,
        compress_tool_results: bool = False,
        max_tool_calls_from_history: Optional[int] = None,
    ):
        llm_config = config or get_llm_config()
        policy = llm_config.policy_for(role)
        self.protocol = policy.protocol
        self.provider = policy.provider
        self.api_key = llm_config.api_key
        self.base_url = openai_compatible_base_url(policy.base_url, "llm.base_url")
        self.model = policy.model
        self.temperature = policy.temperature
        self.reasoning_effort = policy.reasoning_effort
        self.request_timeout_seconds = llm_config.request_timeout_seconds
        self.capabilities = llm_config.capabilities
        self.llm_router = self._build_router(llm_config)
        self.memory_manager = memory_manager
        self.memory_db = memory_db
        self.knowledge = knowledge
        self.knowledge_retriever = knowledge_retriever
        self.tools = tools or []
        self.user_id = user_id
        self.session_id = session_id
        self.tool_call_limit = tool_call_limit
        self.compress_tool_results = compress_tool_results
        self.max_tool_calls_from_history = max_tool_calls_from_history


    def _build_router(self, llm_config) -> LlmRouter:
        """构建端点到路由器：主端点 + 已配置的 fallback 端点。"""
        endpoints = [
            LlmEndpoint(
                name="primary",
                base_url=self.base_url,
                model=self.model,
                api_key=self.api_key,
            )
        ]
        for index, fb in enumerate(getattr(llm_config, "fallbacks", ()) or (), start=1):
            endpoints.append(
                LlmEndpoint(
                    name=f"fallback{index}",
                    base_url=fb.base_url,
                    model=fb.model,
                    api_key=fb.api_key,
                )
            )
        registry_key = tuple(
            (endpoint.name, endpoint.base_url, endpoint.model, endpoint.api_key)
            for endpoint in endpoints
        )
        with _ROUTER_REGISTRY_LOCK:
            router = _ROUTER_REGISTRY.get(registry_key)
            if router is None:
                router = LlmRouter(endpoints, probe_fn=self._endpoint_probe)
                _ROUTER_REGISTRY[registry_key] = router
            return router

    @staticmethod
    def _endpoint_probe(endpoint: LlmEndpoint) -> bool:
        """用同一模型发送极短生成请求，验证真实调用链是否可用。"""
        probe_nonce = uuid.uuid4().hex[:12]
        client = OpenAI(
            api_key=endpoint.api_key,
            base_url=endpoint.base_url,
            timeout=10.0,
            max_retries=0,
            default_headers={"User-Agent": "verifier/1.0"},
        )
        try:
            response = client.chat.completions.create(
                model=endpoint.model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Health probe {probe_nonce}. Reply with OK.",
                    }
                ],
                temperature=0,
                max_tokens=4,
            )
            choices = getattr(response, "choices", None) or []
            if not choices:
                return False
            choice = choices[0]
            message = getattr(choice, "message", None)
            content = str(getattr(message, "content", "") or "").strip()
            reasoning_content = str(
                getattr(message, "reasoning_content", "") or ""
            ).strip()
            finish_reason = str(getattr(choice, "finish_reason", "") or "").strip()
            return bool(content or reasoning_content or finish_reason)
        except Exception:
            return False
    def _validate_config(self) -> None:
        """配置/编程错误必须在重试、降级循环之外直接抛出。

        build_model 与 complete_json 都先过这道校验：缺凭证、协议不支持等属于
        部署/编程错误，不能当作普通请求失败被吞掉后返回 llm_request_failed。
        """
        if self.protocol != "openai_compatible":
            raise ConfigError(f"unsupported LLM protocol: {self.protocol}")
        if not self.api_key:
            raise ConfigError("missing required configuration for llm: llm.api_key")
        if self.tools and not self.capabilities.tool_calls:
            raise ConfigError("configured LLM does not declare tool_calls capability")

    def build_model(
        self,
        *,
        reasoning_effort: Any = _USE_CONFIG,
        endpoint: Optional[LlmEndpoint] = None,
    ) -> OpenAILike:
        """Build the single supported OpenAI-compatible model adapter."""
        self._validate_config()
        endpoint = endpoint or self.llm_router.select()
        model_kwargs = {
            "id": endpoint.model if endpoint else self.model,
            "provider": self.provider,
            "api_key": endpoint.api_key if endpoint else self.api_key,
            "base_url": endpoint.base_url if endpoint else self.base_url,
            "temperature": self.temperature,
            "timeout": self.request_timeout_seconds,
            # Some OpenAI-compatible gateways reject requests that identify as the
            # official OpenAI SDK (User-Agent + X-Stainless-* telemetry headers).
            # Send a neutral User-Agent and strip those SDK headers so the same
            # client works across DeepSeek, private gateways, and local proxies.
            "extra_headers": {
                "User-Agent": "verifier/1.0",
                "X-Stainless-Lang": Omit(),
                "X-Stainless-Package-Version": Omit(),
                "X-Stainless-Os": Omit(),
                "X-Stainless-Arch": Omit(),
                "X-Stainless-Runtime": Omit(),
                "X-Stainless-Runtime-Version": Omit(),
                "X-Stainless-Async": Omit(),
                "X-Stainless-Retry-Count": Omit(),
                "X-Stainless-Read-Timeout": Omit(),
            },
            # Keep one retry owner.  The verifier records and governs attempts
            # below; OpenAI SDK retries would otherwise be invisible and multiply
            # the configured wall-clock budget.
            "max_retries": 0,
            "supports_native_structured_outputs": False,
            "supports_json_schema_outputs": False,
        }
        effective_reasoning_effort = (
            self.reasoning_effort if reasoning_effort is _USE_CONFIG else reasoning_effort
        )
        if effective_reasoning_effort:
            model_kwargs["reasoning_effort"] = effective_reasoning_effort
        return OpenAILike(**model_kwargs)

    def complete_json(self, system: str, user: str, trace_id: Optional[str] = None,
                      reasoning_effort: Any = _USE_CONFIG,
                      output_spec: "StructuredOutputSpec" = None,
                      stage: str = "",
                      tools_override: Any = _USE_CONFIG) -> Dict[str, Any]:
        """
        Complete JSON request with isolated session per trace.

        Args:
            system: System prompt
            user: User prompt
            trace_id: Optional trace ID for session isolation. If provided, creates a unique
                     session for this specific case/trace, preventing cross-case contamination.
            reasoning_effort: Reasoning effort level. Omitted values inherit the selected
                              role policy; explicit None disables deep reasoning.
            output_spec: spec/struct_output.md 结构化输出约束，**必填**。
                所有 LLM 调用都必须过结构化输出协议。如果实在没有明确输出结构（如自由文本分析），
                传 FREE_TEXT_OUTPUT（单字段 result: str）。
                协议层内部：
                - 注入 render_output_constraint 文案到 system prompt（兜底强化）
                - response_format 传 {"type":"json_object"}（DeepSeek 不支持 json_schema）
                - LLM 返回后跑 enforce_output，不合规直接抛 ValueError 阻断
        """
        if output_spec is None:
            raise TypeError(
                "complete_json 缺少 output_spec 参数。"
                "spec/struct_output.md 要求所有 LLM 调用必须传结构化输出约束。"
                "如果确实没有明确输出结构（如自由文本分析），请传 structured_output.FREE_TEXT_OUTPUT。"
            )
        if not self.capabilities.json_mode:
            raise ConfigError("configured LLM does not declare json_mode capability")
        self._validate_config()
        effective_tools = (
            self.tools
            if tools_override is _USE_CONFIG
            else list(tools_override or [])
        )
        effective_tool_call_limit = (
            self.tool_call_limit if effective_tools else None
        )
        model_tools = _json_context_tools(effective_tools)
        effective_tool_call_limit = (
            self.tool_call_limit if model_tools else None
        )
        if trace_id is None:
            import uuid
            trace_id = str(uuid.uuid4())
        from .context_governance import ensure_call_context_governance
        ensure_call_context_governance(
            self,
            project_id=str(getattr(self, "_project_id", "") or "default"),
            role=str(
                getattr(self, "_caller", "")
                or getattr(self, "role", "")
                or "llm"
            ),
            stage=str(stage or "complete_json"),
            trace_id=str(trace_id),
            system=system,
            user=user,
            output_spec=output_spec,
            tools=effective_tools,
        )

        # spec/struct_output.md：注入约束文案 + 返回后强校验阻断
        enforce_spec = output_spec
        from .structured_output import render_output_constraint
        system = system + "\n\n" + render_output_constraint(enforce_spec)

        start_ts = time.time()
        attempt_records: list[Dict[str, Any]] = []
        runtime = {
            "stage": str(stage or ""),
            "attempts": attempt_records,
            "sdk_max_retries": 0,
        }
        try:
            self.llm_router.refresh_health_if_stale()
            # CRITICAL: Use trace-specific session ID to isolate different cases
            # BUT: Prevent conversation history accumulation within same session
            # Each trace gets unique session, prevents cross-case contamination
            effective_session_id = f"{trace_id}:{SESSION_START_TIME}"

            # Retry policy is owned by RuntimeConfig, not copied into this consumer.
            last_exc: Optional[Exception] = None
            result = None
            tried_endpoints: set[str] = set()
            for attempt in range(len(self.llm_router.endpoints)):
                attempt_started = time.monotonic()
                # 降级：每个配置端点在单次请求中最多尝试一次，失败立即切换。
                endpoint = self.llm_router.select(exclude=tried_endpoints)
                model_client = self.build_model(
                    reasoning_effort=reasoning_effort, endpoint=endpoint
                )
                aliases = {}
                for function in model_tools:
                    entrypoint = getattr(function, "entrypoint", None)
                    logical_id = getattr(entrypoint, "logical_tool_id", None)
                    runtime_name = getattr(function, "name", None)
                    if logical_id and runtime_name and logical_id != runtime_name:
                        aliases[logical_id] = runtime_name
                if aliases:
                    object.__setattr__(model_client, "logical_tool_aliases", aliases)
                    object.__setattr__(model_client, "parse_tool_calls", MethodType(_parse_tool_calls_with_aliases, model_client))
                try:
                    agent = Agent(**_supported_agent_kwargs(
                        Agent,
                        {
                            "model": model_client,
                            "system_message": system,
                            "use_json_mode": True,
                            "tools": model_tools,
                            "knowledge": None,
                            "user_id": self.user_id,
                            "session_id": (
                                f"{effective_session_id}:retry{attempt}"
                                if attempt
                                else effective_session_id
                            ),
                            "enable_user_memories": False,
                            "enable_agentic_memory": False,
                            "num_history_runs": 0,
                            "tool_call_limit": effective_tool_call_limit,
                            "compress_tool_results": self.compress_tool_results,
                            "max_tool_calls_from_history": (
                                self.max_tool_calls_from_history
                            ),
                        },
                    ))
                    result = agent.run(user)
                    if _run_failed(result) or not _response_content(result).strip():
                        detail = _response_content(result).strip()
                        if not detail:
                            detail = f"Agno run ended with status {_run_status(result)} and no response content"
                        raise RuntimeError(detail)
                    self.llm_router.record_success(endpoint)
                    attempt_records.append({
                        "attempt": attempt + 1,
                        "endpoint": endpoint.name,
                        "model": endpoint.model,
                        "status": "succeeded",
                        "elapsed_ms": int(
                            (time.monotonic() - attempt_started) * 1000
                        ),
                    })
                    runtime["selected_endpoint"] = endpoint.name
                    runtime["selected_model"] = endpoint.model
                    last_exc = None
                    break
                except Exception as exc:
                    self.llm_router.record_failure(endpoint)
                    tried_endpoints.add(endpoint.name)
                    attempt_records.append({
                        "attempt": attempt + 1,
                        "endpoint": endpoint.name,
                        "model": endpoint.model,
                        "status": "failed",
                        "elapsed_ms": int(
                            (time.monotonic() - attempt_started) * 1000
                        ),
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    })
                    last_exc = exc
                    print(f"[LLM retry] attempt {attempt + 1} failed: {exc}")
            if last_exc is not None and result is None:
                raise last_exc

            # Extract metrics for token tracking
            token_metrics = {}
            if hasattr(result, "metrics") and result.metrics:
                metrics = result.metrics
                token_metrics = {
                    "input_tokens": getattr(metrics, "input_tokens", 0),
                    "output_tokens": getattr(metrics, "output_tokens", 0),
                    "cache_read_tokens": getattr(metrics, "cache_read_tokens", 0),
                    "cache_write_tokens": getattr(metrics, "cache_write_tokens", 0),
                    "reasoning_tokens": getattr(metrics, "reasoning_tokens", 0),
                    "total_tokens": getattr(metrics, "total_tokens", 0),
                }
                print(f"[Token usage] {token_metrics['input_tokens']:,} in + {token_metrics['output_tokens']:,} out + {token_metrics['cache_read_tokens']:,} cache = {token_metrics['total_tokens']:,} total")
        except Exception as exc:
            _track_context(
                self,
                system,
                user,
                None,
                trace_id or "",
                {},
                int((time.time() - start_ts) * 1000),
                str(exc),
                runtime=runtime,
            )
            return {"error": "llm_request_failed", "raw_text": str(exc)}

        content = _response_content(result)
        status = _run_status(result)
        if _run_failed(result) or not content.strip():
            if _run_failed(result):
                error_code = "llm_request_failed"
                detail = content.strip() or f"Agno run ended with status {status} and no response content"
            else:
                error_code = "llm_empty_response"
                detail = "LLM run completed without response content"
            raw_response = _raw_response(result)
            elapsed_ms = int((time.time() - start_ts) * 1000)
            _track_context(
                self,
                system,
                user,
                result,
                trace_id or "",
                token_metrics,
                elapsed_ms,
                detail,
                runtime=runtime,
            )
            return {
                "error": error_code,
                "raw_text": detail,
                "raw_model_response": raw_response,
            }

        tool_call_log = _extract_tool_call_log(result)
        tool_budget_error = _tool_budget_error(
            tool_call_log, effective_tool_call_limit
        )
        if tool_budget_error:
            runtime["tool_budget"] = {
                "configured_limit": int(effective_tool_call_limit),
                "actual_calls": len(tool_call_log),
                "status": "exceeded",
            }
            elapsed_ms = int((time.time() - start_ts) * 1000)
            _track_context(
                self,
                system,
                user,
                result,
                trace_id or "",
                token_metrics,
                elapsed_ms,
                tool_budget_error,
                runtime=runtime,
            )
            return {
                "error": "tool_budget_exceeded",
                "raw_text": tool_budget_error,
                "tool_call_log": tool_call_log,
            }

        try:
            try:
                parsed = extract_json(content)
            except JsonExtractionError:
                parsed = None
            parsed = _select_schema_matching_object(content, parsed, enforce_spec)
            if parsed is None:
                # Re-run to preserve the full user-facing parse diagnostics.
                parsed = extract_json(content)
        except JsonExtractionError as exc:
            raw_response = _raw_response(result)
            elapsed_ms = int((time.time() - start_ts) * 1000)
            _track_context(
                self,
                system,
                user,
                result,
                trace_id or "",
                token_metrics,
                elapsed_ms,
                str(exc),
                runtime=runtime,
            )
            raise ValueError(f"[{getattr(self, '_caller', '') or 'llm'}] {exc}") from exc
        raw_response = _raw_response(result)
        elapsed_ms = int((time.time() - start_ts) * 1000)

        # spec/struct_output.md：强校验阻断，不放行假货
        from .structured_output import enforce_output
        caller = getattr(self, "_caller", "") or ""
        enforce_output(parsed, enforce_spec, caller=caller)

        # Add token metrics to raw_response if available
        if token_metrics:
            if isinstance(raw_response, dict):
                raw_response["metrics"] = token_metrics

        if isinstance(parsed, dict):
            parsed.setdefault("raw_model_response", raw_response)
            # 从 agno RunOutput 提取 tool call log
            if token_metrics:
                parsed.setdefault("metrics", token_metrics)
            if tool_call_log:
                parsed.setdefault("_tool_call_log", tool_call_log)
            _track_context(
                self,
                system,
                user,
                result,
                trace_id,
                token_metrics,
                elapsed_ms,
                None,
                runtime=runtime,
            )
            return parsed
        _track_context(
            self,
            system,
            user,
            result,
            trace_id or "",
            token_metrics,
            elapsed_ms,
            None,
            runtime=runtime,
        )
        return {"value": parsed, "raw_model_response": raw_response}
