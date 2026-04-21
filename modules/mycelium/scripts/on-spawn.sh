#!/bin/bash
# @hook agentSpawn
# @priority 20
# @module mycelium
# @writes nutrient
# @description Remind about undigested spores
set -euo pipefail

MEMORY="python3.12 $FUNGUS_HOME/hooks/memory.py"

# Load network memory with summaries
summaries=$($MEMORY query --sql \
  "SELECT summary FROM memory WHERE stage='network' AND summary != ''")
if [ -n "$summaries" ]; then
  echo "<memory>"
  while IFS= read -r line; do
    echo "- $line"
  done <<< "$summaries"
  echo "</memory>"
fi

# Check for undigested spores
count=$($MEMORY count --stage spore)
[ "$count" = "0" ] && exit 0

echo "<mycelium-reminder>"
echo "$count undigested spores pending."
echo "Ask the user if they want to digest now."
echo "If confirmed, read modules/mycelium/SKILL.md for instructions."
echo "</mycelium-reminder>"
