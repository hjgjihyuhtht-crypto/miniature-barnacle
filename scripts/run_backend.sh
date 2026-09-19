#!/usr/bin/env bash
# Start / restart NEXUS AI backend on this machine.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/uvicorn" ]]; then
  echo "ERROR: venv missing. Run: bash server/scripts/setup.sh"
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env — edit NEXUS_API_KEY and OPENROUTER_API_KEY before production use."
fi

mkdir -p "$ROOT/data/db" "$ROOT/data/uploads" "$ROOT/data/audio"
mkdir -p "$ROOT/logs"

# Stop previous uvicorn if any
pkill -f 'uvicorn backend.main:app' 2>/dev/null || true
sleep 1

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

nohup uvicorn backend.main:app --host "$HOST" --port "$PORT" \
  >"$ROOT/logs/backend.log" 2>&1 &
echo "Backend PID $!  →  http://${HOST}:${PORT}"
sleep 2
curl -fsS "http://${HOST}:${PORT}/health" && echo
