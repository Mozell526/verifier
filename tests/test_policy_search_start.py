from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT / "impl/projects/policy_search/scripts/start.sh"


def _prepare_fixture(tmp_path: Path, *, dotenv: str) -> tuple[Path, Path, Path]:
    verifier_root = tmp_path / "verifier"
    script = verifier_root / "impl/projects/policy_search/scripts/start.sh"
    script.parent.mkdir(parents=True)
    shutil.copy2(START_SCRIPT, script)
    script.chmod(0o755)
    (verifier_root / ".env").write_text(dotenv, encoding="utf-8")

    business_root = tmp_path / "policy-search"
    uvicorn = business_root / ".venv/bin/uvicorn"
    uvicorn.parent.mkdir(parents=True)
    uvicorn.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s' \"${DASHSCOPE_API_KEY-}\" > \"${CAPTURE_FILE}\"\n"
        "printf '%s' \"$*\" >> \"${CAPTURE_FILE}\"\n",
        encoding="utf-8",
    )
    uvicorn.chmod(0o755)
    return verifier_root, script, business_root


def _run_start(script: Path, business_root: Path, capture_file: Path) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.environ["PATH"],
        "POLICY_SEARCH_REPO": str(business_root),
        "CAPTURE_FILE": str(capture_file),
    }
    return subprocess.run(
        ["bash", str(script)],
        cwd=business_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_policy_search_start_maps_verifier_bailian_key_to_dashscope(tmp_path: Path) -> None:
    _, script, business_root = _prepare_fixture(tmp_path, dotenv="BAILIAN_API_KEY=test-bailian-key\n")
    capture_file = tmp_path / "capture"

    result = _run_start(script, business_root, capture_file)

    assert result.returncode == 0
    captured = capture_file.read_text(encoding="utf-8")
    assert captured.startswith("test-bailian-key")
    assert "main:main_app" in captured


def test_policy_search_start_fails_without_verifier_bailian_key(tmp_path: Path) -> None:
    _, script, business_root = _prepare_fixture(tmp_path, dotenv="BAILIAN_API_KEY=\n")
    capture_file = tmp_path / "capture"

    result = _run_start(script, business_root, capture_file)

    assert result.returncode != 0
    assert "BAILIAN_API_KEY must be configured" in result.stderr
    assert not capture_file.exists()


def test_policy_search_is_user_managed() -> None:
    from impl.core.project_loader import load_project

    spec = load_project("policy_search")

    assert spec.runtime["mode"] == "existing_service_required"
    assert spec.local_deployment_enabled is False
