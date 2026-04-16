#!/bin/bash
# @hook agent-spawn
# @priority 20
# @module mycelium
# @writes nutrient
# @description Remind about undigested spores
set -euo pipefail

MEMORY="$FUNGUS_HOME/hooks/memory.sh"

# Clean stale entries before loading
bash "$MEMORY" clean

# Load network memory
network=$(bash "$MEMORY" list --stage network)
if [ -n "$network" ]; then
  echo "<memory>"
  echo "$network"
  echo "</memory>"
fi

# Check for undigested spores
count=$(bash "$MEMORY" count --stage spore)
[ "$count" = "0" ] && exit 0

echo "<mycelium-reminder>"
echo "$count undigested spores pending."
echo "Ask the user if they want to digest now."
echo "If confirmed, read modules/mycelium/SKILL.md for instructions."
echo "</mycelium-reminder>"
