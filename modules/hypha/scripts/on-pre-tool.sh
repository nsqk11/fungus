#!/bin/bash
# @hook pre-tool-use
# @priority 10
# @module hypha
# @writes spore
# @description Capture tool intent as spore
set -euo pipefail

# uses $FUNGUS_HOME from substrate.sh
STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

bash "$FUNGUS_HOME/hooks/memory.sh" add \
  --stage spore \
  --hook pre-tool-use \
  --source agent \
  --data "$STDIN"
