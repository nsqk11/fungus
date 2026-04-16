#!/bin/bash
# Substrate — signal conductor for Fungus modules.
# Routes hook events to matching module scripts.
# Usage: substrate.sh <hook-name> [stdin-data]
set -euo pipefail

HOOK="${1:?Usage: substrate.sh <hook-name> [agent-name]}"
export FUNGUS_HOME="$(cd "$(dirname "$0")/.." && pwd)"
export FUNGUS_AGENT="${2:-default}"

STDIN_DATA=""
[ ! -t 0 ] && STDIN_DATA=$(cat)

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
  if [ -n "$STDIN_DATA" ]; then
    printf '%s' "$STDIN_DATA" | $runner "$script"
  else
    $runner "$script"
  fi
done <<< "$SCRIPTS"
