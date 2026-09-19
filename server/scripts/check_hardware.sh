#!/usr/bin/env bash
set -euo pipefail

echo "=== NEXUS AI hardware check ==="
echo "CPU:"
lscpu 2>/dev/null | egrep 'Model name|Socket|CPU\(s\)|Thread|Architecture' || nproc
echo
echo "RAM:"
free -h || true
echo
echo "Disk:"
df -h / /opt 2>/dev/null || df -h /
echo
echo "GPU (if any):"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
else
  echo "No nvidia-smi (CPU-only mode expected)."
fi
echo
echo "Python:"
python3 --version || true
echo
echo "Recommended free disk for both models: >= 40 GB"
