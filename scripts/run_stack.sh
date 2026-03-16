#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

bash "$ROOT_DIR/scripts/run_backend.sh" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Backend failed to start on port ${PORT:-8080}. Check the backend log above or change PORT." >&2
  wait "$BACKEND_PID" || true
  exit 1
fi

npm run dev
