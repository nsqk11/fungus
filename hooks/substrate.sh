#!/bin/bash
# Substrate — signal conductor for Fungus modules.
# Routes hook events to matching module scripts.
# Reads hook_event_name from stdin JSON payload.
set -euo pipefail

export FUNGUS_HOME="$(cd "$(dirname "$0")/.." && pwd)"

STDIN_DATA=""
[ ! -t 0 ] && STDIN_DATA=$(cat)
[ -z "$STDIN_DATA" ] && exit 0

HOOK=$(printf '%s' "$STDIN_DATA" | python3.12 -c "import sys,json; print(json.load(sys.stdin).get('hook_event_name',''))")
[ -z "$HOOK" ] && exit 0

# Python resolves which scripts to run and in what order
SCRIPTS=$(python3.12 "$FUNGUS_HOME/hooks/substrate.py" "$HOOK" "$FUNGUS_HOME")
[ -z "$SCRIPTS" ] && exit 0

# Execute each script, forwarding stdin
while IFS='|' read -r script module; do
  name=$(basename "$script")
  echo "[substrate] $HOOK → $name ($module)" >&2
  if [[ "$script" == *.py ]]; then
    runner="python3.12"
  else
    runner="bash"
  fi
  printf '%s' "$STDIN_DATA" | $runner "$script"
done <<< "$SCRIPTS"
