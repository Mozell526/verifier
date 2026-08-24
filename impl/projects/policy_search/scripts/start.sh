#!/usr/bin/env bash
set -euo pipefail

: "${POLICY_SEARCH_REPO:?POLICY_SEARCH_REPO must point to the policy-search repository}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
verifier_root="$(cd -- "${script_dir}/../../../.." && pwd)"
verifier_env="${verifier_root}/.env"

value="$(awk -F= '$1 == "BAILIAN_API_KEY" { print substr($0, index($0, "=") + 1); found = 1 } END { if (!found) exit 1 }' "${verifier_env}")"
if [[ -z "${value}" ]]; then
  echo "BAILIAN_API_KEY must be configured in ${verifier_env}" >&2
  exit 1
fi

export DASHSCOPE_API_KEY="${value}"

exec "${POLICY_SEARCH_REPO}/.venv/bin/uvicorn" main:main_app \
  --app-dir "${POLICY_SEARCH_REPO}" \
  --host 127.0.0.1 \
  --port 8050
