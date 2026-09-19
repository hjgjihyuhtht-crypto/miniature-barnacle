#!/usr/bin/env bash
# Download Llama 3.1 8B Instruct (Hugging Face). Does NOT start without confirmation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env" || true

TARGET="${LLAMA_MODEL_PATH:-/opt/nexus-ai/models/llama}"
MODEL_ID="${LLAMA_MODEL_ID:-meta-llama/Llama-3.1-8B-Instruct}"
FORMAT="${1:-transformers}" # transformers | gguf

echo "NEXUS AI — Llama download"
echo "Model:  $MODEL_ID"
echo "Target: $TARGET"
echo "Format: $FORMAT"
echo
echo "This can require 10–20+ GB of disk and HF license acceptance."
read -r -p "Continue? [y/N] " ans
[[ "${ans:-}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

mkdir -p "$TARGET"
export HF_TOKEN="${HF_TOKEN:-}"

if [[ "$FORMAT" == "gguf" ]]; then
  echo "Downloading GGUF (example: bartowski / community quant)."
  echo "Set GGUF_REPO and GGUF_FILE env vars for the exact file."
  GGUF_REPO="${GGUF_REPO:-bartowski/Meta-Llama-3.1-8B-Instruct-GGUF}"
  GGUF_FILE="${GGUF_FILE:-Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$GGUF_REPO" "$GGUF_FILE" --local-dir "$TARGET" --local-dir-use-symlinks False
  else
    pip install -U "huggingface_hub[cli]"
    huggingface-cli download "$GGUF_REPO" "$GGUF_FILE" --local-dir "$TARGET" --local-dir-use-symlinks False
  fi
else
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$MODEL_ID" --local-dir "$TARGET" --local-dir-use-symlinks False
  else
    pip install -U "huggingface_hub[cli]"
    huggingface-cli download "$MODEL_ID" --local-dir "$TARGET" --local-dir-use-symlinks False
  fi
fi

echo "Done. Files in $TARGET"
find "$TARGET" -maxdepth 2 -type f | head -n 30
