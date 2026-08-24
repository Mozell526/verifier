#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFIER_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${VERIFIER_ROOT}/.env"
RUNTIME_DIR="${VERIFIER_ROOT}/tmp/client_search-runtime"
PID_FILE="${RUNTIME_DIR}/service.pid"
LOG_FILE="${RUNTIME_DIR}/service.log"
RUNNER_FILE="${RUNTIME_DIR}/service-runner.sh"
LAUNCHD_LABEL="${CLIENT_SEARCH_LAUNCHD_LABEL:-com.verifier.client-search.8000}"
LAUNCHD_DOMAIN="gui/$(id -u)"
PORT="${CLIENT_SEARCH_PORT:-8000}"
BASE_URL="${CLIENT_SEARCH_BASE_URL:-http://127.0.0.1:${PORT}}"
STARTUP_TIMEOUT_SECONDS="${CLIENT_SEARCH_STARTUP_TIMEOUT_SECONDS:-240}"
REQUEST_TIMEOUT_SECONDS="${CLIENT_SEARCH_REQUEST_TIMEOUT_SECONDS:-120}"

usage() {
  cat <<USAGE
Usage: $0 {start|stop|restart|status|logs}

Environment overrides:
  CLIENT_SEARCH_REPO                    Business repository (normally loaded from verifier/.env)
  PYTHON_EXECUTABLE                     Python used to start the business service
  CLIENT_SEARCH_PORT                    Service port (default: 8000)
  CLIENT_SEARCH_BASE_URL                Service URL (default: http://127.0.0.1:<port>)
  CLIENT_SEARCH_STARTUP_TIMEOUT_SECONDS Startup/reindex wait timeout (default: 240)
  CLIENT_SEARCH_REQUEST_TIMEOUT_SECONDS Parse request timeout (default: 120)
  CLIENT_SEARCH_LAUNCHD_LABEL             macOS launchd label
USAGE
}

load_environment() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi

  : "${CLIENT_SEARCH_REPO:?CLIENT_SEARCH_REPO must be configured in ${ENV_FILE} or the process environment}"
  CLIENT_SEARCH_REPO="$(cd "${CLIENT_SEARCH_REPO}" && pwd)"
  APP_DIR="${CLIENT_SEARCH_REPO}/src/main/python"
  MAIN_FILE="${APP_DIR}/main.py"
  ROUTE_FILE="${APP_DIR}/api/client_search_query_parse_post.py"
  PYTHON_BIN="${PYTHON_EXECUTABLE:-}"

  if [[ -z "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="$(python -c 'from impl.core.config import get_python_config; print(get_python_config().executable)' 2>/dev/null || true)"
  fi
  if [[ -z "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="$(command -v python3 || command -v python || true)"
  fi

  [[ -d "${CLIENT_SEARCH_REPO}/.git" ]] || {
    echo "client_search repository is missing or is not a Git checkout: ${CLIENT_SEARCH_REPO}" >&2
    exit 1
  }
  [[ -f "${MAIN_FILE}" && -f "${ROUTE_FILE}" ]] || {
    echo "client_search service entrypoint is missing under: ${APP_DIR}" >&2
    exit 1
  }
  [[ -n "${PYTHON_BIN}" && -x "${PYTHON_BIN}" ]] || {
    echo "Python executable is unavailable: ${PYTHON_BIN:-<empty>}" >&2
    exit 1
  }

  mkdir -p "${RUNTIME_DIR}"
}

listener_pids() {
  lsof -tiTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true
}

launchd_available() {
  [[ "$(uname -s)" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1
}

launchd_service_loaded() {
  launchd_available && launchctl print "${LAUNCHD_DOMAIN}/${LAUNCHD_LABEL}" >/dev/null 2>&1
}

launchd_job_pid() {
  launchctl print "${LAUNCHD_DOMAIN}/${LAUNCHD_LABEL}" 2>/dev/null |
    awk '/^[[:space:]]*pid = / { print $3; exit }'
}

remove_launchd_service() {
  if launchd_service_loaded; then
    launchctl remove "${LAUNCHD_LABEL}" >/dev/null 2>&1 || true
  fi
}

write_service_runner() {
  {
    printf '#!/usr/bin/env bash\n'
    printf 'cd %q\n' "${APP_DIR}"
    printf 'exec env PYTHONUNBUFFERED=1 API_PORT=%q %q main.py\n' "${PORT}" "${PYTHON_BIN}"
  } > "${RUNNER_FILE}"
  chmod 700 "${RUNNER_FILE}"
}

pid_cwd() {
  local pid="$1"
  lsof -a -p "${pid}" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1
}

is_client_search_process() {
  local pid="$1"
  local cwd
  cwd="$(pid_cwd "${pid}")"
  [[ -n "${cwd}" ]] || return 1
  [[ -f "${cwd}/src/main/python/api/client_search_query_parse_post.py" ]] || \
    [[ -f "${cwd}/api/client_search_query_parse_post.py" ]]
}

wait_for_process_exit() {
  local pid="$1"
  local attempts=30
  while kill -0 "${pid}" 2>/dev/null && (( attempts > 0 )); do
    sleep 1
    attempts=$((attempts - 1))
  done
  if kill -0 "${pid}" 2>/dev/null; then
    echo "process ${pid} did not stop after 30 seconds" >&2
    return 1
  fi
}

stop_managed_service() {
  if launchd_service_loaded; then
    echo "stopping launchd service ${LAUNCHD_LABEL}"
    remove_launchd_service
  fi

  local pids=""
  if [[ -f "${PID_FILE}" ]]; then
    pids="$(cat "${PID_FILE}" 2>/dev/null || true)"
  fi
  if [[ -z "${pids}" ]] || ! kill -0 "${pids}" 2>/dev/null; then
    pids="$(listener_pids)"
  fi

  if [[ -z "${pids}" ]]; then
    rm -f "${PID_FILE}"
    echo "client_search service is not running"
    return 0
  fi

  local pid
  for pid in ${pids}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      continue
    fi
    if [[ -f "${PID_FILE}" ]] || is_client_search_process "${pid}"; then
      echo "stopping client_search pid=${pid} cwd=$(pid_cwd "${pid}")"
      kill "${pid}"
      wait_for_process_exit "${pid}"
    else
      echo "refusing to stop unknown process pid=${pid} on port ${PORT}; cwd=$(pid_cwd "${pid}")" >&2
      exit 1
    fi
  done
  rm -f "${PID_FILE}"
}

require_elasticsearch() {
  local es_url="${ES_HOST:-http://127.0.0.1:9200}"
  if ! curl -fsS --max-time 5 "${es_url}" >/dev/null; then
    echo "Elasticsearch is unavailable at ${es_url}; start.md requires it before client_search startup" >&2
    exit 1
  fi
  echo "Elasticsearch ready: ${es_url}"
}

wait_for_liveness() {
  local url="$1"
  local deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if curl -fsS --max-time 10 "${url}" >/dev/null 2>&1; then
      return 0
    fi
    if [[ -f "${PID_FILE}" ]]; then
      local pid
      pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
      if [[ -n "${pid}" ]] && ! kill -0 "${pid}" 2>/dev/null; then
        echo "client_search exited before becoming ready; last log lines:" >&2
        tail -n 100 "${LOG_FILE}" >&2 || true
        return 1
      fi
    fi
    sleep 2
  done
  echo "timed out waiting for ${url}; last log lines:" >&2
  tail -n 100 "${LOG_FILE}" >&2 || true
  return 1
}

reindex_fields() {
  echo "submitting field reindex"
  local response
  response="$(curl -fsS --max-time 30 -X POST \
    -H 'Content-Type: application/json' \
    --data '{"force_reindex_fields":true}' \
    "${BASE_URL}/api/v1/fields/reindex")"
  printf '%s' "${response}" | "${PYTHON_BIN}" -c '
import json, sys
body = json.load(sys.stdin)
if body.get("success") is not True:
    raise SystemExit(f"field reindex rejected: {body}")
print("field reindex accepted")
'
}

verify_parse_endpoint() {
  local trace_id="start-check-$(date +%s)"
  local payload
  payload="$(printf '{"source":"verifier-start","user_text":"大于50岁的客户","session_id":"verifier-start","trace_id":"%s","user_id":"verifier","user_action":"write","action_scenario":"customerSearch","extra_input_params":{}}' "${trace_id}")"
  local deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))

  echo "waiting for client_search parse endpoint"
  while (( SECONDS < deadline )); do
    local response
    response="$(curl -sS --max-time "${REQUEST_TIMEOUT_SECONDS}" \
      -H 'Content-Type: application/json' \
      --data "${payload}" \
      "${BASE_URL}/api/v1/client_search_query_parse_no_encipher" 2>/dev/null || true)"
    if [[ -n "${response}" ]] && printf '%s' "${response}" | "${PYTHON_BIN}" -c '
import json, sys
try:
    body = json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
if body.get("code") != 0 or not isinstance(body.get("data"), dict):
    raise SystemExit(1)
extra = body["data"].get("extra_output_params") or {}
print("parse endpoint ready:", json.dumps({
    "query_logic": extra.get("query_logic"),
    "conditions": extra.get("conditions"),
    "matched_level": extra.get("matched_level"),
}, ensure_ascii=False))
'; then
      return 0
    fi

    if [[ -f "${PID_FILE}" ]]; then
      local pid
      pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
      if [[ -n "${pid}" ]] && ! kill -0 "${pid}" 2>/dev/null; then
        echo "client_search exited before the parse endpoint became ready; last log lines:" >&2
        tail -n 100 "${LOG_FILE}" >&2 || true
        return 1
      fi
    fi
    sleep 2
  done

  echo "timed out waiting for the client_search parse endpoint; last log lines:" >&2
  tail -n 100 "${LOG_FILE}" >&2 || true
  return 1
}

start_service() {
  require_elasticsearch

  local existing
  existing="$(listener_pids)"
  if [[ -n "${existing}" ]]; then
    echo "port ${PORT} is occupied; replacing the existing client_search service"
    stop_managed_service
  fi

  : > "${LOG_FILE}"
  echo "starting client_search"
  echo "  repository: ${CLIENT_SEARCH_REPO}"
  echo "  python:     ${PYTHON_BIN}"
  echo "  url:        ${BASE_URL}"
  echo "  log:        ${LOG_FILE}"

  rm -f "${PID_FILE}"
  local pid=""
  if launchd_available; then
    remove_launchd_service
    write_service_runner
    launchctl submit -l "${LAUNCHD_LABEL}" -o "${LOG_FILE}" -e "${LOG_FILE}" -- "${RUNNER_FILE}"
    local attempts=20
    while [[ -z "${pid}" && ${attempts} -gt 0 ]]; do
      pid="$(launchd_job_pid || true)"
      [[ -n "${pid}" ]] || sleep 0.25
      attempts=$((attempts - 1))
    done
    [[ -n "${pid}" ]] && echo "${pid}" > "${PID_FILE}"
  else
    (
      cd "${APP_DIR}"
      nohup env PYTHONUNBUFFERED=1 API_PORT="${PORT}" "${PYTHON_BIN}" main.py \
        </dev/null >>"${LOG_FILE}" 2>&1 &
      echo "$!" > "${PID_FILE}"
    )
    pid="$(cat "${PID_FILE}")"
  fi

  wait_for_liveness "${BASE_URL}/"
  echo "client_search liveness check passed"
  reindex_fields
  verify_parse_endpoint
  pid="$(listener_pids | head -1)"
  [[ -n "${pid}" ]] && echo "${pid}" > "${PID_FILE}"
  echo "client_search startup completed (pid=${pid:-unknown})"
}

show_status() {
  local pids
  pids="$(listener_pids)"
  if [[ -z "${pids}" ]]; then
    echo "client_search is stopped (port ${PORT} is not listening)"
    return 1
  fi
  echo "client_search listener pid(s): ${pids}"
  local pid
  for pid in ${pids}; do
    echo "  pid=${pid} cwd=$(pid_cwd "${pid}")"
  done
  curl -fsS --max-time 30 "${BASE_URL}/health" | "${PYTHON_BIN}" -m json.tool
}

show_logs() {
  [[ -f "${LOG_FILE}" ]] || {
    echo "log file does not exist: ${LOG_FILE}" >&2
    exit 1
  }
  tail -n 200 -f "${LOG_FILE}"
}

main() {
  local command="${1:-start}"
  load_environment
  case "${command}" in
    start) start_service ;;
    stop) stop_managed_service ;;
    restart) stop_managed_service; start_service ;;
    status) show_status ;;
    logs) show_logs ;;
    -h|--help|help) usage ;;
    *) usage >&2; exit 2 ;;
  esac
}

main "$@"
