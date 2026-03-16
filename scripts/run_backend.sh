#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  echo "Missing backend virtualenv at backend/.venv. Run: python3 -m venv backend/.venv && source backend/.venv/bin/activate && pip install -r backend/requirements.txt" >&2
  exit 1
fi

if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/backend/.env"
  set +a
fi

if [[ -n "${DEALWHISPER_RUNTIME_MODE:-}" ]]; then
  export LIVE_RUNTIME_MODE="$DEALWHISPER_RUNTIME_MODE"
fi

export PYTHONPATH="$ROOT_DIR/backend"

exec "$ROOT_DIR/backend/.venv/bin/python" -m uvicorn \
  dealwhisper_backend.server:app \
  --app-dir "$ROOT_DIR/backend" \
  --host 127.0.0.1 \
  --port "${PORT:-8080}" \
  --reload
