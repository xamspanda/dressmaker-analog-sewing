#!/usr/bin/env bash
# Build the release zip dist/AnalogSewing-<version>.zip (extract into the game folder; needs BepInEx 5).
# Needs a Dressmaker install with BepInEx to compile against (see DRESSMAKER_DIR in the csproj).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SDK_VER=0.9.1
SDK_ZIP="wooting-analog-sdk-v$SDK_VER-x86_64-pc-windows-msvc.zip"
SDK_SHA256=27b3b868f4005018d3638e0f485942272134e1e09be1db1747ccc63f33fc187a
VERSION="$(sed -n 's:.*<Version>\(.*\)</Version>.*:\1:p' "$ROOT/src/AnalogSewing/AnalogSewing.csproj")"

CACHE="$ROOT/build/cache"
STAGE="$ROOT/build/stage"
mkdir -p "$CACHE" "$ROOT/dist"
rm -rf "$STAGE"

# Wooting's redistributable SDK, pinned and checksummed.
if [[ ! -f "$CACHE/$SDK_ZIP" ]]; then
  curl -fsSL -o "$CACHE/$SDK_ZIP.part" "https://github.com/WootingKb/wooting-analog-sdk/releases/download/v$SDK_VER/$SDK_ZIP"
  mv "$CACHE/$SDK_ZIP.part" "$CACHE/$SDK_ZIP"
fi
echo "$SDK_SHA256  $CACHE/$SDK_ZIP" | sha256sum -c --quiet

dotnet build "$ROOT/src/AnalogSewing" -c Release -nologo -v quiet

PLUGIN="$STAGE/mod/BepInEx/plugins/AnalogSewing"
mkdir -p "$PLUGIN"
cp "$ROOT/src/AnalogSewing/bin/Release/net472/AnalogSewing.dll" "$PLUGIN/"
bsdtar -xOf "$CACHE/$SDK_ZIP" release/wooting_analog_sdk_dist.dll > "$PLUGIN/wooting_analog_sdk_dist.dll"
cp "$ROOT/LICENSE" "$PLUGIN/LICENSE.txt"
cp "$ROOT/THIRD_PARTY_NOTICES.md" "$PLUGIN/THIRD_PARTY_NOTICES.md"

MOD_ZIP="$ROOT/dist/AnalogSewing-$VERSION.zip"
rm -f "$MOD_ZIP"
(cd "$STAGE/mod" && zip -qr "$MOD_ZIP" BepInEx)

echo "Built:"
unzip -l "$MOD_ZIP" | sed -n '4,$p'
