#!/bin/bash
# @hook stop
# @priority 10
# @module hypha
# @reads spore
# @writes spore
# @description Capture assistant response and tool chain as spores
set -euo pipefail

stdin=$(cat)
[ -z "$stdin" ] && exit 0

memory() {
  python3.12 "$FUNGUS_HOME/hooks/memory.py" "$@"
}

# Store stop spore
memory add --stage spore --hook stop --data "$stdin"

# Find boundary: last userPromptSubmit id
boundary=$(memory query --sql \
  "SELECT id FROM memory WHERE hook='userPromptSubmit' ORDER BY id DESC LIMIT 1")
[ -z "$boundary" ] && exit 0

# Validate boundary is numeric (defense against injection)
[[ "$boundary" =~ ^[0-9]+$ ]] || exit 0

# Collect tool names from preToolUse spores after boundary
chain=$(memory query --sql \
  "SELECT json_extract(data, '\$.tool_name') FROM memory
   WHERE hook='preToolUse' AND id > '$boundary'
     AND json_extract(data, '\$.tool_name') NOT IN
         ('fs_read','fs_write','grep','glob','code','todo_list')")
[ -z "$chain" ] && exit 0

# Aggregate into comma-separated string
tools=$(echo "$chain" | paste -sd,)

# Delete aggregated preToolUse spores
memory query --sql \
  "DELETE FROM memory WHERE hook='preToolUse' AND id > '$boundary'" >/dev/null

memory add \
  --stage spore \
  --hook toolChain \
  --data "{\"tools\":\"$tools\"}"
