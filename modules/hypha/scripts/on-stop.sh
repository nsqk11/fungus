#!/bin/bash
# @hook stop
# @priority 10
# @module hypha
# @reads spore
# @writes spore
# @description Capture assistant response and tool chain as spores
set -euo pipefail

STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

MEMORY="$FUNGUS_HOME/hooks/memory.sh"

# Store stop spore
bash "$MEMORY" add --stage spore --hook stop --data "$STDIN"

# Extract tool chain for this turn
# Use last userPromptSubmit spore ID as boundary (IDs are monotonic)
CHAIN=$(bash "$MEMORY" query --jq '
  ([.[] | select(.hook == "userPromptSubmit")] | last | .id) as $bid |
  if $bid then
    [.[] | select(.hook == "preToolUse" and .id > $bid)
      | .data.tool_name
      | select(. != "fs_read" and . != "fs_write" and . != "grep" and . != "glob" and . != "code" and . != "todo_list")] |
    if length > 0 then join(",") else empty end
  else empty end
')

[ -z "$CHAIN" ] && exit 0

# Delete individual preToolUse spores that were aggregated
bash "$MEMORY" query --jq '
  ([.[] | select(.hook == "userPromptSubmit")] | last | .id) as $bid |
  [.[] | select(.hook == "preToolUse" and .id > $bid) | .id] | .[]
' | while read -r pid; do
  bash "$MEMORY" delete "$pid" >/dev/null 2>&1
done

bash "$MEMORY" add \
  --stage spore \
  --hook toolChain \
  --data "{\"tools\":\"$CHAIN\"}"
