#!/bin/bash
# @hook agentSpawn
# @priority 20
# @module mycelium
# @writes nutrient
# @description Remind about undigested spores
set -euo pipefail

MEMORY="$FUNGUS_HOME/hooks/memory.sh"

# Clean stale entries before loading
bash "$MEMORY" clean

# Load network memory with summaries
network_ids=$(bash "$MEMORY" list --stage network | awk '{print $1}')
if [ -n "$network_ids" ]; then
  echo "<memory>"
  for id in $network_ids; do
    summary=$(bash "$MEMORY" get "$id" | python3 -c "import sys,json; print(json.load(sys.stdin).get('summary',''))" 2>/dev/null)
    [ -n "$summary" ] && echo "- $summary"
  done
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
