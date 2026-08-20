from __future__ import annotations

import pytest

from impl.core.live_transport import LiveTransport
from impl.core.mock_agent import load_live_schema
from impl.core.project_loader import load_project
from impl.projects.llm_probe import live_schema as probe_schema
from impl.projects.llm_probe.capability import resolve_capability
from impl.projects.llm_probe.live import LlmProbeLive, resolve_http


def test_request_requires_capability_xor_and_url_or_ref():
    check = probe_schema.check
    assert check.request({"body": {"q": 1}, "capability_ref": "client_search"})
    assert check.request({
        "body": {"q": 1},
        "url": "http://127.0.0.1/x",
        "capability": "echo JSON",
    })
    assert not check.request({"body": {"q": 1}})
    assert not check.request({"body": {"q": 1}, "capability": "echo JSON"})
    assert not check.request({"body": {"q": 1}, "url": "http://127.0.0.1/x"})
    assert not check.request({"body": {"q": 1}, "capability_ref": "missing_project"})


def test_load_live_schema_keeps_probe_xor_check():
    loaded = load_live_schema("llm_probe")
    assert loaded.check is probe_schema.check
    assert loaded.check.request({"body": {"q": 1}, "capability_ref": "client_search"})
    assert not loaded.check.request({"body": {"q": 1}})


def test_explicit_capability_wins_over_map():
    assert resolve_capability({
        "capability": "custom probe",
        "capability_ref": "client_search",
    }) == "custom probe"
    text = resolve_capability({"capability_ref": "client_search"})
    assert "搜索条件" in text


def test_resolve_http_sends_nested_body_and_maps_capability_ref_url():
    spec = load_project("llm_probe")
    url, method, headers, body, timeout = resolve_http(
        {
            "body": {"user_text": "张伟"},
            "capability_ref": "client_search",
            "headers": {"X-Trace": "1"},
        },
        spec,
    )
    assert body == {"user_text": "张伟"}
    assert method == "POST"
    assert headers == {"X-Trace": "1"}
    assert timeout > 0
    client = load_project("client_search").require_service("primary")
    expected = str(client["base_url"]).rstrip("/") + "/" + str(client["endpoint"]).lstrip("/")
    assert url == expected


def test_extract_output_stringifies_response_body():
    live = LlmProbeLive(load_project("llm_probe"))
    assert live.extract_output([{"ok": True}]) == {"output_text": '{"ok": true}'}
    assert live.extract_output(["plain"]) == {"output_text": "plain"}
    assert live.extract_output([]) == {"output_text": ""}


def test_streaming_response_is_rejected(monkeypatch):
    class StreamResponse:
        status = 200
        headers = {"Content-Type": "text/event-stream"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def getcode(self):
            return self.status

        def read(self):
            return b"data: hi\n\n"

    monkeypatch.setattr(
        "impl.core.live_transport.urllib.request.urlopen",
        lambda request, timeout=0: StreamResponse(),
    )
    live = LlmProbeLive(load_project("llm_probe"))
    with pytest.raises(RuntimeError, match="text/event-stream"):
        live.deliver_real(
            {
                "body": {"q": 1},
                "url": "http://127.0.0.1:9/llm-probe",
                "method": "POST",
                "capability": "echo JSON",
            },
            LiveTransport(),
        )
