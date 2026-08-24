#!/usr/bin/env bash
# Idempotent Cloud Agent install for the verifier project.
# Prepares a `python` binary and the full Python dependency set.
set -euo pipefail

cd "$(dirname "$0")/.."

# run.sh bootstraps the correct interpreter via the literal `python` command,
# but the base image ships only `python3`. Provide `python` when it is missing.
if ! command -v python >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python-is-python3
fi

echo "python: $(command -v python) ($(python --version 2>&1))"

# Install dependencies into the user site. Re-running is a no-op once satisfied.
python -m pip install --user --no-warn-script-location -r .cursor/requirements.txt

# Fail fast if the runtime cannot import its critical modules.
python - <<'PY'
from agno.agent import Agent  # noqa: F401
import dashscope, openai, fastapi, uvicorn, selenium, openpyxl  # noqa: F401
import json_repair, yaml, requests  # noqa: F401
print("verifier dependency import check: OK")
PY
