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

MEMORY="python3.12 $FUNGUS_HOME/hooks/memory.py"

# Store stop spore
$MEMORY add --stage spore --hook stop --data "$STDIN"

# Find boundary: last userPromptSubmit id
BOUNDARY=$($MEMORY query --sql \
  "SELECT id FROM memory WHERE hook='userPromptSubmit' ORDER BY id DESC LIMIT 1")
[ -z "$BOUNDARY" ] && exit 0

# Collect tool names from preToolUse spores after boundary
CHAIN=$($MEMORY query --sql \
  "SELECT json_extract(data, '\$.tool_name') FROM memory
   WHERE hook='preToolUse' AND id > '$BOUNDARY'
     AND json_extract(data, '\$.tool_name') NOT IN
         ('fs_read','fs_write','grep','glob','code','todo_list')")
[ -z "$CHAIN" ] && exit 0

# Aggregate into comma-separated string
TOOLS=$(echo "$CHAIN" | paste -sd,)

# Delete aggregated preToolUse spores
$MEMORY query --sql \
  "DELETE FROM memory WHERE hook='preToolUse' AND id > '$BOUNDARY'" >/dev/null

$MEMORY add \
  --stage spore \
  --hook toolChain \
  --data "{\"tools\":\"$TOOLS\"}"
