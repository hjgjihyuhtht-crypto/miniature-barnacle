#!/usr/bin/env bash
# Build NEXUS AI Android APK with Flet (run on a Linux VPS / PC with ≥20 GB free).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== NEXUS AI — build APK ==="

# Prefer project venv
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing '$1'. Install it first."; exit 1; }; }
need python3
need git
need unzip
need curl

# Flet downloads Google's Linux Android cmdline-tools (x86_64 only). Flutter also
# lacks android host artifacts (gen_snapshot, etc.) for linux-arm64.
ARCH="$(uname -m)"
if [[ "$ARCH" != "x86_64" && "$ARCH" != "amd64" ]]; then
  echo "ERROR: APK build requires Linux x86_64 (this host is ${ARCH})."
  echo
  echo "Flet/Flutter Android tooling does not support Linux aarch64:"
  echo "  - Android cmdline-tools: Linux-x86_64 only"
  echo "  - Flutter gen_snapshot for Android: linux-x64 host artifacts only"
  echo
  echo "Build on an x86_64 Linux VPS/PC, or use a cloud CI runner (GitHub Actions"
  echo "ubuntu-latest). The backend can still run fine on aarch64."
  exit 1
fi

# Disk check (Flutter + Android SDK need a lot of space)
FREE_KB="$(df -Pk "$ROOT" | awk 'NR==2{print $4}')"
FREE_GB=$((FREE_KB / 1024 / 1024))
echo "Free disk: ~${FREE_GB} GB"
if (( FREE_GB < 15 )); then
  echo "WARNING: recommend ≥20 GB free. Build may fail with 'No space left on device'."
fi

# Ensure packaging deps
python3 -m pip install -U pip >/dev/null
python3 -m pip install -r "$ROOT/requirements-app.txt" flet-cli >/dev/null

VERSION="${BUILD_VERSION:-1.0.0}"
NUMBER="${BUILD_NUMBER:-1}"
OUT="${OUT_DIR:-$ROOT/build/apk}"

mkdir -p "$OUT"

echo "Building APK (product=NEXUS AI, org=com.nexusai)…"
flet build apk "$ROOT" \
  --product "NEXUS AI" \
  --org com.nexusai \
  --project nexus-ai \
  --build-version "$VERSION" \
  --build-number "$NUMBER" \
  --module-name main \
  --exclude .venv backend tests data server scripts __pycache__ .git .github build \
  --yes \
  --permissions microphone \
  --skip-flutter-doctor \
  -o "$OUT"

echo
echo "=== Done ==="
mapfile -t APKS < <(find "$OUT" "$ROOT/build" -name '*.apk' -type f 2>/dev/null | sort -u)
if ((${#APKS[@]})); then
  for f in "${APKS[@]}"; do
    ls -lh "$f"
  done
  echo
  echo "Install on phone: adb install -r <arquivo.apk>"
  echo "Or copy the APK to the device and open it."
else
  echo "ERROR: no .apk found under $OUT"
  exit 1
fi
