#!/usr/bin/env bash
# Package the mod and install it into a local Dressmaker folder for testing,
# installing BepInEx 5 there first if it's missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DRESSMAKER_DIR="${DRESSMAKER_DIR:-$HOME/.local/share/Steam/steamapps/common/Dressmaker}"
BEPINEX_VER=5.4.23.5
BEPINEX_SHA256=82f9878551030f54657792c0740d9d51a09500eeae1fba21106b0c441e6732c4

[[ -f "$DRESSMAKER_DIR/Dressmaker.exe" ]] || { echo "Dressmaker.exe not found in $DRESSMAKER_DIR (set DRESSMAKER_DIR)"; exit 1; }

if [[ ! -f "$DRESSMAKER_DIR/BepInEx/core/BepInEx.dll" ]]; then
  zip="$ROOT/build/cache/BepInEx_win_x64_$BEPINEX_VER.zip"
  mkdir -p "$(dirname "$zip")"
  [[ -f "$zip" ]] || curl -fsSL -o "$zip" \
    "https://github.com/BepInEx/BepInEx/releases/download/v$BEPINEX_VER/BepInEx_win_x64_$BEPINEX_VER.zip"
  echo "$BEPINEX_SHA256  $zip" | sha256sum -c --quiet
  bsdtar -xf "$zip" -C "$DRESSMAKER_DIR"
  echo "Installed BepInEx $BEPINEX_VER"
fi

"$ROOT/scripts/package.sh" >/dev/null
VERSION="$(sed -n 's:.*<Version>\(.*\)</Version>.*:\1:p' "$ROOT/src/AnalogSewing/AnalogSewing.csproj")"
rm -f "$DRESSMAKER_DIR/BepInEx/plugins/AnalogSew.dll"   # pre-release name
rm -f "$DRESSMAKER_DIR"/BepInEx/plugins/AnalogSewing/{AnalogSewing,wooting_analog_sdk_dist}.dll   # 1.0.0 layout
bsdtar -xf "$ROOT/dist/AnalogSewing-$VERSION.zip" -C "$DRESSMAKER_DIR"
echo "Installed Analog Sewing $VERSION into $DRESSMAKER_DIR"
