#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="/tmp/o2c_quality_backend.log"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/.env"
  set +a
fi

STARTED_BACKEND=0
BACKEND_PID=""

is_backend_up() {
  curl --max-time 2 -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1
}

cleanup() {
  if [[ "$STARTED_BACKEND" -eq 1 && -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
    echo "Temporary backend stopped."
  fi
}

trap cleanup EXIT

cd "$ROOT"

echo "[1/4] Backend tests"
"$ROOT/.venv/bin/python" -m pytest backend/tests -q

echo "[2/4] Frontend tests"
cd "$ROOT/frontend"
npm test -- --run

echo "[3/4] Frontend build"
npm run build

cd "$ROOT"
echo "[4/4] API smoke checks (expects backend on :8000)"
if ! is_backend_up; then
  echo "Backend not detected on :8000, starting temporary backend..."
  cd "$ROOT"
  "$ROOT/.venv/bin/python" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1 &
  BACKEND_PID="$!"
  STARTED_BACKEND=1

  for _ in {1..20}; do
    if is_backend_up; then
      break
    fi
    sleep 0.3
  done
fi

if ! is_backend_up; then
  echo "Backend did not become ready on :8000."
  if [[ -f "$BACKEND_LOG" ]]; then
    echo "--- backend log tail ---"
    tail -n 40 "$BACKEND_LOG" || true
    echo "--- end backend log tail ---"
  fi
  exit 1
fi

curl -fsS http://127.0.0.1:8000/api/agents/status >/dev/null
curl -fsS http://127.0.0.1:8000/api/graph/overview >/dev/null
TRACE_ID="$(curl -fsS -X POST http://127.0.0.1:8000/api/query/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"Tell me a joke about football"}' \
  | "$ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["trace_id"])')"
curl -fsS "http://127.0.0.1:8000/api/query/trace/${TRACE_ID}" >/dev/null
echo "API smoke checks passed."

if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  echo "[5/5] Gemini integration smoke check"
  LLM_STATUS="$(curl -fsS -X POST http://127.0.0.1:8000/api/query/ask \
    -H 'Content-Type: application/json' \
    -d '{"query":"Show top 5 customers by sales orders"}' \
    | "$ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"

  if [[ "$LLM_STATUS" == "error" ]]; then
    echo "Gemini smoke check failed (status=error)."
    exit 1
  fi
  echo "Gemini smoke check passed (status=${LLM_STATUS})."
else
  echo "[5/5] Gemini integration smoke check skipped (GEMINI_API_KEY not set)."
fi

echo "Quality gate passed."
