#!/bin/bash
# @hook agent-spawn
# @priority 20
# @module mycelium
# @writes nutrient
# @description Load network memory and list undigested spores
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
MEMORY="$REPO_ROOT/hooks/memory.sh"

# Load network memory
network=$(bash "$MEMORY" list --stage network)
if [ -n "$network" ]; then
  echo "<memory>"
  echo "$network"
  echo "</memory>"
fi

# List undigested spores
spores=$(bash "$MEMORY" list --stage spore)
[ -z "$spores" ] && exit 0

echo "<undigested-spores>"
echo "$spores"
echo "</undigested-spores>"
