#!/bin/bash
# @hook stop
# @priority 10
# @module hypha
# @writes spore
# @description Capture assistant response and tool chain as spores
set -euo pipefail

STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

MEMORY="$FUNGUS_HOME/hooks/memory.sh"

# Store stop spore
bash "$MEMORY" add --stage spore --hook stop --data "$STDIN"

# Extract tool chain for this turn
# Find the last userPromptSubmit timestamp, collect preToolUse tool_names after it
CHAIN=$(jq -r '
  ([.[] | select(.hook == "userPromptSubmit")] | last | .timestamp) as $t |
  if $t then
    [.[] | select(.hook == "preToolUse" and .timestamp >= $t) | .data.tool_name] |
    if length > 0 then join(",") else empty end
  else empty end
' "$FUNGUS_HOME/data/memory.json" 2>/dev/null)

[ -z "$CHAIN" ] && exit 0

# Delete individual preToolUse spores that were aggregated
jq -r --arg t "$( jq -r '[.[] | select(.hook == "userPromptSubmit")] | last | .timestamp' "$FUNGUS_HOME/data/memory.json" )" \
  '[.[] | select(.hook == "preToolUse" and .timestamp >= $t) | .id] | .[]' \
  "$FUNGUS_HOME/data/memory.json" 2>/dev/null | while read -r pid; do
  bash "$MEMORY" delete "$pid" >/dev/null 2>&1
done

bash "$MEMORY" add \
  --stage spore \
  --hook toolChain \
  --data "{\"tools\":\"$CHAIN\"}"
