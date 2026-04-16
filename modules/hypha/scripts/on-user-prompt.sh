#!/bin/bash
# @hook user-prompt-submit
# @priority 10
# @module hypha
# @writes spore
# @description Capture user prompt as spore
set -euo pipefail

[ -f "$FUNGUS_HOME/data/.hypha-lock" ] && exit 0

# uses $FUNGUS_HOME from substrate.sh
STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

bash "$FUNGUS_HOME/hooks/memory.sh" add \
  --stage spore \
  --hook user-prompt-submit \
  --source user \
  --data "$STDIN"
