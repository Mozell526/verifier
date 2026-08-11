from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .config import ROOT, get_runtime_config
from .config_bootstrap import effective_environment_snapshot
from .config_schema import ConfigError, RuntimeConfig


_CAPABILITY_PROBE = r"""
import importlib.metadata
import json
import sys

import inspect
from agno.agent import Agent

kwargs = {
    "compress_tool_results": False,
    "max_tool_calls_from_history": None,
}
params = inspect.signature(Agent.__init__).parameters
if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
    kwargs = {key: value for key, value in kwargs.items() if key in params}
Agent(**kwargs)
if sys.argv[1] == "1":
    import dashscope  # noqa: F401
print(json.dumps({
    "python_executable": sys.executable,
    "python_version": sys.version.split()[0],
    "agno_version": importlib.metadata.version("agno"),
}))
"""


@dataclass(frozen=True)
class RuntimeCapabilityResult:
    python_executable: str
    python_version: str = ""
    agno_version: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


def probe_runtime_capabilities(
    config: RuntimeConfig,
    *,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
) -> RuntimeCapabilityResult:
    """Probe capabilities in the exact interpreter selected by RuntimeConfig."""
    effective_env = dict(effective_environment_snapshot(root / ".env", environ))
    embedding_probe = "1" if config.embedding.enabled else "0"
    try:
        completed = subprocess.run(
            [config.python.executable, "-c", _CAPABILITY_PROBE, embedding_probe],
            cwd=root,
            env=effective_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return RuntimeCapabilityResult(
            python_executable=config.python.executable,
            error=f"cannot execute configured Python: {exc}",
        )
    output = completed.stdout.strip()
    if completed.returncode != 0:
        tail = output[-1000:] if output else f"exit code {completed.returncode}"
        return RuntimeCapabilityResult(
            python_executable=config.python.executable,
            error=f"configured runtime capability probe failed: {tail}",
        )
    try:
        payload = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return RuntimeCapabilityResult(
            python_executable=config.python.executable,
            error=f"configured runtime returned invalid probe output: {exc}",
        )
    return RuntimeCapabilityResult(
        python_executable=str(payload.get("python_executable") or config.python.executable),
        python_version=str(payload.get("python_version") or ""),
        agno_version=str(payload.get("agno_version") or ""),
    )


def ensure_runtime_ready(
    config: RuntimeConfig | None = None,
    *,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
) -> RuntimeCapabilityResult:
    resolved = config or get_runtime_config()
    resolved.require("llm")
    if resolved.embedding.enabled:
        resolved.require("embedding")
    result = probe_runtime_capabilities(resolved, root=root, environ=environ)
    if not result.ok:
        raise ConfigError(result.error)
    return result


def main() -> int:
    try:
        result = ensure_runtime_ready()
    except ConfigError as exc:
        print(f"runtime-preflight: failed: {exc}")
        return 1
    print(
        "runtime-preflight: ok "
        f"python={result.python_executable} "
        f"python_version={result.python_version} agno={result.agno_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
