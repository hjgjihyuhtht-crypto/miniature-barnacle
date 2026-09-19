#!/usr/bin/env bash
# Bootstrap NEXUS AI on a Linux VPS (no auto giant model download).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "NEXUS AI setup"
bash "$ROOT/server/scripts/check_hardware.sh"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env — edit NEXUS_API_KEY and optional provider keys."
fi

# Prefer Debian/Ubuntu python3 over Termux Android python when both are on PATH
# (PRoot/Termux hybrid: Android SOABI cannot install pydantic-core wheels).
resolve_python() {
  local cand soabi
  for cand in /usr/bin/python3 /bin/python3 "$(command -v python3 || true)"; do
    [[ -x "$cand" ]] || continue
    soabi="$("$cand" -c 'import sysconfig; print(sysconfig.get_config_var("SOABI") or "")' 2>/dev/null || true)"
    if [[ "$soabi" == *linux-gnu* ]]; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(resolve_python || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: need a glibc Linux Python 3 (SOABI *-linux-gnu)." >&2
  echo "On PRoot/Termux do NOT use /data/data/com.termux/.../python3 for the venv." >&2
  echo "Install: apt install python3 python3-venv python3-pip" >&2
  exit 1
fi
echo "Using Python: $PYTHON_BIN ($("$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_config_var("SOABI"))'))"

if [[ -d "$ROOT/.venv" ]]; then
  OLD_SOABI="$("$ROOT/.venv/bin/python" -c 'import sysconfig; print(sysconfig.get_config_var("SOABI") or "")' 2>/dev/null || true)"
  if [[ "$OLD_SOABI" == *android* ]]; then
    echo "Removing broken Android-SOABI venv ($OLD_SOABI)"
    rm -rf "$ROOT/.venv"
  fi
fi

"$PYTHON_BIN" -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install -U pip
pip install -r "$ROOT/requirements.txt"

mkdir -p /opt/nexus-ai/models/llama /opt/nexus-ai/models/qwen "$ROOT/data/db" "$ROOT/data/uploads" "$ROOT/data/audio" || true

echo
echo "Next steps:"
echo "  1. Edit $ROOT/.env"
echo "  2. Optional: bash server/scripts/download_llama.sh"
echo "  3. Optional: bash server/scripts/download_qwen.sh"
echo "  4. Optional: bash server/scripts/setup_swap.sh 16"
echo "  5. Run: source .venv/bin/activate && uvicorn backend.main:app --host 127.0.0.1 --port 8000"
echo "  6. Diagnose: bash server/scripts/nexus-doctor"
