#!/usr/bin/env bash
# Steam launch wrapper: run the Linux bridge for as long as the game runs.
# Only needed when the mod's built-in Wooting SDK can't see the keyboard under Proton.
#   Launch options: /path/to/with-bridge.sh %command%
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/dressmaker-bridge.log"
mkdir -p "$(dirname "$LOG")"

# A bridge already running in a terminal does the same job; don't start a second one.
if ! pgrep -f '^(/usr/bin/)?python3? [^ ]*wooting-bridge\.py' >/dev/null; then
  python3 "$HERE/wooting-bridge.py" --debug >"$LOG" 2>&1 &
  bridge=$!
  trap 'kill "$bridge" 2>/dev/null' EXIT
fi

"$@"
