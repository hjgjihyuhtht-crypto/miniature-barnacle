#!/usr/bin/env bash
# Download Qwen 2.5 7B Instruct. Does NOT start without confirmation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env" || true

TARGET="${QWEN_MODEL_PATH:-/opt/nexus-ai/models/qwen}"
MODEL_ID="${QWEN_MODEL_ID:-Qwen/Qwen2.5-7B-Instruct}"
FORMAT="${1:-transformers}"

echo "NEXUS AI — Qwen download"
echo "Model:  $MODEL_ID"
echo "Target: $TARGET"
echo "Format: $FORMAT"
echo
echo "This can require ~15 GB of disk."
read -r -p "Continue? [y/N] " ans
[[ "${ans:-}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

mkdir -p "$TARGET"
export HF_TOKEN="${HF_TOKEN:-}"

if [[ "$FORMAT" == "gguf" ]]; then
  GGUF_REPO="${GGUF_REPO:-Qwen/Qwen2.5-7B-Instruct-GGUF}"
  GGUF_FILE="${GGUF_FILE:-qwen2.5-7b-instruct-q4_k_m.gguf}"
  pip install -U "huggingface_hub[cli]" >/dev/null
  huggingface-cli download "$GGUF_REPO" "$GGUF_FILE" --local-dir "$TARGET" --local-dir-use-symlinks False
else
  pip install -U "huggingface_hub[cli]" >/dev/null
  huggingface-cli download "$MODEL_ID" --local-dir "$TARGET" --local-dir-use-symlinks False
fi

echo "Done. Files in $TARGET"
find "$TARGET" -maxdepth 2 -type f | head -n 30
