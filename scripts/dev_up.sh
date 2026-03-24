#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID_FILE="/tmp/o2c_backend.pid"
FRONTEND_PID_FILE="/tmp/o2c_frontend.pid"
BACKEND_LOG="/tmp/o2c_backend.log"
FRONTEND_LOG="/tmp/o2c_frontend.log"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/.env"
  set +a
fi

for p in 8000 3000; do
  lsof -ti tcp:"$p" | xargs -r kill -9 || true
done

cd "$ROOT"
nohup "$ROOT/.venv/bin/python" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1 &
echo $! > "$BACKEND_PID_FILE"

cd "$ROOT/frontend"
nohup npm run dev -- --host 127.0.0.1 --port 3000 > "$FRONTEND_LOG" 2>&1 &
echo $! > "$FRONTEND_PID_FILE"

sleep 2

echo "Backend:  http://127.0.0.1:8000 (pid $(cat "$BACKEND_PID_FILE"))"
echo "Frontend: http://127.0.0.1:3000 (pid $(cat "$FRONTEND_PID_FILE"))"
echo "Health:   $(curl --max-time 5 -sS http://127.0.0.1:8000/api/health || echo FAILED)"
