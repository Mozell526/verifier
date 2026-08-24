from __future__ import annotations

import json
from pathlib import Path

import pytest

from impl.core.config import resolve_runtime_config
from impl.core.config_schema import ConfigError
from impl.core.runtime_preflight import ensure_runtime_ready, probe_runtime_capabilities


ROOT = Path(__file__).resolve().parents[1]


def _resolved(tmp_path: Path, *, embedding_enabled: bool = True):
    environ = {"DEEPSEEK_API_KEY": "llm-key"}
    if embedding_enabled:
        environ["BAILIAN_API_KEY"] = "embedding-key"
    else:
        environ["EMBEDDING_ENABLED"] = "false"
    return resolve_runtime_config(
        config_path=ROOT / "impl" / "config.yaml",
        dotenv_path=tmp_path / ".env",
        environ=environ,
    )


def test_runtime_probe_uses_selected_interpreter_and_embedding_capability(tmp_path, monkeypatch):
    resolved = _resolved(tmp_path)
    captured = {}

    def completed(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return type("Completed", (), {
            "returncode": 0,
            "stdout": json.dumps({
                "python_executable": "/selected/python",
                "python_version": "3.11.14",
                "agno_version": "2.3.21",
            }),
        })()

    monkeypatch.setattr("impl.core.runtime_preflight.subprocess.run", completed)

    result = probe_runtime_capabilities(resolved, root=ROOT, environ={})

    assert result.ok
    assert captured["args"][0] == resolved.python.executable
    assert captured["args"][-1] == "1"
    assert result.agno_version == "2.3.21"


def test_runtime_preflight_requires_enabled_embedding_secret_before_probe(tmp_path, monkeypatch):
    resolved = resolve_runtime_config(
        config_path=ROOT / "impl" / "config.yaml",
        dotenv_path=tmp_path / ".env",
        environ={"DEEPSEEK_API_KEY": "llm-key"},
    )
    monkeypatch.setattr(
        "impl.core.runtime_preflight.subprocess.run",
        lambda *_args, **_kwargs: pytest.fail("capability probe must not run before required values pass"),
    )

    with pytest.raises(ConfigError, match="embedding.api_key"):
        ensure_runtime_ready(resolved, root=ROOT, environ={})


def test_runtime_preflight_allows_explicitly_disabled_embedding(tmp_path, monkeypatch):
    resolved = _resolved(tmp_path, embedding_enabled=False)

    def completed(_args, **kwargs):
        assert _args[-1] == "0"
        return type("Completed", (), {
            "returncode": 0,
            "stdout": json.dumps({
                "python_executable": "/selected/python",
                "python_version": "3.11.14",
                "agno_version": "2.3.21",
            }),
        })()

    monkeypatch.setattr("impl.core.runtime_preflight.subprocess.run", completed)

    assert ensure_runtime_ready(resolved, root=ROOT, environ={}).ok
