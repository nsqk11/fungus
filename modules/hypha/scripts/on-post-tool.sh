#!/bin/bash
# @hook post-tool-use
# @priority 10
# @module hypha
# @writes spore
# @description Capture tool result as spore
set -euo pipefail

[ -f "$FUNGUS_HOME/data/.hypha-lock" ] && exit 0

# uses $FUNGUS_HOME from substrate.sh
STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

bash "$FUNGUS_HOME/hooks/memory.sh" add \
  --stage spore \
  --hook post-tool-use \
  --source environment \
  --data "$STDIN"
