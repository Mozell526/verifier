"""看门狗单测：流式事件流挂住时，总时长到点必须抛 TimeoutError（走既有端点切换），而不是无限等。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator

from impl.core import llm_client as m


@dataclass
class FakeRunOutput:
    content: str = "ok"
    status: str = "COMPLETED"


class SlowDripAgent:
    """模拟"连接活着、隔很久滴一个字节、总时长远超预期"的流式调用。"""

    def __init__(self, **_kwargs):
        pass

    def run(self, _user, *, stream: bool = False, yield_run_output: bool = False, **_kw):
        assert stream and yield_run_output
        return self._events()

    def _events(self) -> Iterator[object]:
        # 每 0.05 秒滴一个事件，永不结束——读超时抓不住它，只有看门狗能
        while True:
            time.sleep(0.05)
            yield object()


def test_stream_watchdog_aborts_never_ending_drip(monkeypatch):
    monkeypatch.setattr(m, "Agent", SlowDripAgent)
    agent = SlowDripAgent()
    started = time.monotonic()
    try:
        m._run_agent(agent, "hi", stream=True, wall_deadline=time.monotonic() + 0.2)
        raise AssertionError("expected TimeoutError")
    except TimeoutError as exc:
        elapsed = time.monotonic() - started
        assert 0.15 <= elapsed < 1.5, f"watchdog fired at {elapsed:.2f}s"
        assert "wall-clock deadline" in str(exc)


def test_stream_watchdog_not_triggered_when_stream_completes(monkeypatch):
    class FastAgent:
        def __init__(self, **_kwargs):
            pass

        def run(self, _user, *, stream: bool = False, yield_run_output: bool = False, **_kw):
            assert stream and yield_run_output
            return iter([object(), object(), FakeRunOutput()])

    result = m._run_agent(FastAgent(), "hi", stream=True, wall_deadline=time.monotonic() + 30)
    assert m._response_content(result) == "ok"


def test_non_stream_ignores_deadline():
    agent = SlowDripAgent()
    # 非流式分支保持原样：不迭代事件流，deadline 不参与
    import types
    calls = {}

    class LegacyAgent:
        def __init__(self, **_kwargs):
            pass

        def run(self, _user, **kwargs):
            calls.update(kwargs)
            return FakeRunOutput()

    result = m._run_agent(LegacyAgent(), "hi", stream=False, wall_deadline=time.monotonic() + 0.05)
    assert m._response_content(result) == "ok"
    assert "stream" not in calls and "yield_run_output" not in calls
