#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  printf 'Configure o ambiente primeiro com: npm run setup\n' >&2
  exit 1
fi
backend_pid=''
frontend_pid=''
worker_pid=''
beat_pid=''
cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$backend_pid" ]]; then kill "$backend_pid" 2>/dev/null || true; fi
  if [[ -n "$frontend_pid" ]]; then kill "$frontend_pid" 2>/dev/null || true; fi
  if [[ -n "$worker_pid" ]]; then kill "$worker_pid" 2>/dev/null || true; fi
  if [[ -n "$beat_pid" ]]; then kill "$beat_pid" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
(cd backend && exec ../.venv/bin/python -m uvicorn src.main:app --reload) &
backend_pid=$!
(cd backend && exec ../.venv/bin/python -m celery -A src.celery_app:app worker --loglevel=info --concurrency=2) &
worker_pid=$!
(cd backend && exec ../.venv/bin/python -m celery -A src.celery_app:app beat --loglevel=info --schedule=/tmp/esports-celerybeat-schedule) &
beat_pid=$!
(cd frontend && exec node node_modules/react-scripts/scripts/start.js) &
frontend_pid=$!
wait -n "$backend_pid" "$frontend_pid" "$worker_pid" "$beat_pid"
