"""LLM 端点降级公共设施（公共设施，所有 Role/调用方复用）。

解决单一 LLM 端点长时间不可用导致等待/失败的问题：
- 主端点 + 按优先级排序的 fallback 端点池；
- 每个端点维护 circuit-breaker 健康状态机：healthy / cooling / probing；
- 请求时选当前健康且优先级最高的端点；单次请求内失败即切下一个端点（被动降级）；
- 冷却期到后用最小 ping 后台探活，恢复后自动回切；
- 对上游调用方（LlmClient / Judge / Attribute）透明，正常时零额外请求。

本模块不依赖具体 LLM SDK 与配置结构，只接收端点候选列表与一个可注入的 ping 函数，
因此可独立测试、自由复用于任何 LLM 客户端。
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Callable, Collection, List, Optional

__all__ = [
    "LlmEndpoint",
    "LlmRouter",
    "EndpointHealth",
    "DEFAULT_COOLDOWN_SECONDS",
]


# 冷却期：端点被打入冷却后，至少等这么久才允许 probe。用户拍板 3 分钟。
DEFAULT_COOLDOWN_SECONDS = 180.0
DEFAULT_HEALTH_TTL_SECONDS = 180.0
DEFAULT_PROBE_WAIT_SECONDS = 10.0

# 连续失败达到该阈值才真正把端点降级（避免单次抖动导致乒乓切换）。
FAILURE_THRESHOLD = 2


@dataclass(frozen=True)
class LlmEndpoint:
    """一个可选的 LLM 端点（构造参数透传给 LLM SDK）。"""

    name: str
    base_url: str
    model: str
    api_key: str

    def to_sdk_kwargs(self) -> dict:
        return {
            "id": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
        }


@dataclass
class EndpointHealth:
    """单个端点的 circuit-breaker 健康状态。线程安全。"""

    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    last_health_at: float = 0.0

    def in_cooldown(self, now: float) -> bool:
        return self.cooldown_until > now

    def health_is_fresh(self, now: float, ttl_seconds: float) -> bool:
        return self.last_health_at > 0.0 and now - self.last_health_at < ttl_seconds


class LlmRouter:
    """按优先级调度多个 LLM 端点，失败自动降级、冷却后自动恢复。

    ``probe_fn`` 是一个可注入的函数：接收一个 ``LlmEndpoint``，成功返回 True、
    失败返回 False。默认不探测（只依赖被动降级），调用方可按需注入真实 ping。
    """

    def __init__(
        self,
        endpoints: List[LlmEndpoint],
        *,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        health_ttl_seconds: float = DEFAULT_HEALTH_TTL_SECONDS,
        probe_wait_seconds: float = DEFAULT_PROBE_WAIT_SECONDS,
        failure_threshold: int = FAILURE_THRESHOLD,
        probe_fn: Optional[Callable[[LlmEndpoint], bool]] = None,
    ) -> None:
        if not endpoints:
            raise ValueError("llm_router requires at least one endpoint")
        self.endpoints: List[LlmEndpoint] = list(endpoints)
        self.cooldown_seconds = cooldown_seconds
        self.health_ttl_seconds = health_ttl_seconds
        self.probe_wait_seconds = probe_wait_seconds
        self.failure_threshold = int(failure_threshold)
        self._probe_fn = probe_fn
        self._health: dict[str, EndpointHealth] = {
            ep.name: EndpointHealth() for ep in self.endpoints
        }
        self._lock = threading.Lock()
        self._refresh_condition = threading.Condition(self._lock)
        self._refreshing = False

    # ---- 状态查询 ----------------------------------------------------------

    def _candidate_order(self, now: float) -> List[LlmEndpoint]:
        """按优先级返回当前可用（非冷却）端点。"""
        return [
            ep for ep in self.endpoints if not self._health[ep.name].in_cooldown(now)
        ]

    def select(self, *, exclude: Collection[str] = ()) -> LlmEndpoint:
        """返回当前应使用的端点（最高优先级且可用）。

        ``exclude``：同一请求内已经尝试过的端点名。每个端点在单次业务请求中
        最多执行一次，避免重复撞击坏端点并确保备用端点不会被遗漏。
        """
        with self._lock:
            now = time.monotonic()
            candidates = self._candidate_order(now)
            available = [ep for ep in candidates if ep.name not in exclude]
            if not available:
                if candidates:
                    raise RuntimeError("no untried llm endpoint remains")
                raise RuntimeError("all llm endpoints are cooling")
            return available[0]

    def active_endpoint_names(self) -> List[str]:
        with self._lock:
            now = time.monotonic()
            return [ep.name for ep in self._candidate_order(now)]

    # ---- 成功/失败上报 ------------------------------------------------------

    def record_success(self, endpoint: LlmEndpoint) -> None:
        with self._lock:
            health = self._health[endpoint.name]
            health.consecutive_failures = 0
            health.cooldown_until = 0.0
            health.last_health_at = time.monotonic()

    def record_failure(self, endpoint: LlmEndpoint) -> None:
        with self._lock:
            health = self._health[endpoint.name]
            health.consecutive_failures += 1
            if health.consecutive_failures >= self.failure_threshold:
                health.cooldown_until = (
                    time.monotonic() + self.cooldown_seconds
                )

    def _record_probe_result(self, endpoint: LlmEndpoint, ok: bool) -> None:
        now = time.monotonic()
        with self._lock:
            health = self._health[endpoint.name]
            health.last_health_at = now
            if ok:
                health.consecutive_failures = 0
                health.cooldown_until = 0.0
            else:
                health.consecutive_failures = self.failure_threshold
                health.cooldown_until = now + self.cooldown_seconds

    def refresh_health_if_stale(self) -> None:
        """并行真实探测过期端点；并发请求复用同一轮探测结果。"""
        if self._probe_fn is None:
            return
        with self._refresh_condition:
            now = time.monotonic()
            stale = [
                endpoint
                for endpoint in self.endpoints
                if not self._health[endpoint.name].in_cooldown(now)
                and not self._health[endpoint.name].health_is_fresh(
                    now, self.health_ttl_seconds
                )
            ]
            if not stale:
                return
            if self._refreshing:
                self._refresh_condition.wait(timeout=self.probe_wait_seconds)
                return
            self._refreshing = True

        executor = ThreadPoolExecutor(
            max_workers=len(stale), thread_name_prefix="llm-health-probe"
        )
        futures = {executor.submit(self._probe_fn, endpoint): endpoint for endpoint in stale}
        done, pending = wait(futures, timeout=self.probe_wait_seconds)
        for future in done:
            endpoint = futures[future]
            try:
                ok = bool(future.result())
            except Exception:
                ok = False
            self._record_probe_result(endpoint, ok)
        for future in pending:
            future.cancel()
            self._record_probe_result(futures[future], False)
        executor.shutdown(wait=False, cancel_futures=True)

        with self._refresh_condition:
            self._refreshing = False
            self._refresh_condition.notify_all()
