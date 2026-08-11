#!/usr/bin/env bash
set -euo pipefail

: "${POLICY_SEARCH_REPO:?POLICY_SEARCH_REPO must point to the policy-search repository}"

exec "${POLICY_SEARCH_REPO}/.venv/bin/uvicorn" main:main_app \
  --app-dir "${POLICY_SEARCH_REPO}" \
  --host 127.0.0.1 \
  --port 8050
