#!/usr/bin/env bash
# Optional local runtime extras (not installed by default — large).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

echo "Install optional NEXUS runtimes (confirm each)."
echo "1) llama-cpp-python (GGUF)"
echo "2) torch + transformers (HF)"
echo "3) faster-whisper (STT)"
echo "4) sentence-transformers (embeddings)"
echo "5) vllm (GPU only)"
read -r -p "Choice [1-5/N]: " c
case "${c:-}" in
  1) pip install llama-cpp-python ;;
  2) pip install torch transformers accelerate ;;
  3) pip install faster-whisper ;;
  4) pip install sentence-transformers ;;
  5) pip install vllm ;;
  *) echo "Aborted." ;;
esac
