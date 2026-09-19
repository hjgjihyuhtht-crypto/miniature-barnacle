#!/usr/bin/env bash
# Create / enlarge swap for low-RAM VPS (interactive).
set -euo pipefail

SIZE_GB="${1:-16}"
SWAPFILE="${SWAPFILE:-/swapfile}"

echo "NEXUS AI — setup swap (${SIZE_GB}G -> $SWAPFILE)"
read -r -p "Continue? [y/N] " ans
[[ "${ans:-}" =~ ^[Yy]$ ]] || exit 1

if swapon --show | grep -q .; then
  echo "Existing swap:"
  swapon --show
fi

if [[ -f "$SWAPFILE" ]]; then
  echo "Swapfile already exists: $SWAPFILE"
  exit 0
fi

fallocate -l "${SIZE_GB}G" "$SWAPFILE" || dd if=/dev/zero of="$SWAPFILE" bs=1G count="$SIZE_GB"
chmod 600 "$SWAPFILE"
mkswap "$SWAPFILE"
swapon "$SWAPFILE"
grep -q "$SWAPFILE" /etc/fstab || echo "$SWAPFILE none swap sw 0 0" >> /etc/fstab
echo "Swap ready."
free -h
