#!/bin/bash
# @hook userPromptSubmit
# @priority 10
# @module hypha
# @writes spore
# @description Capture user prompt as spore
set -euo pipefail

STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

# Drop trivial prompts (≤ 5 characters)
PROMPT=$(printf '%s' "$STDIN" | python3.12 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))")
[ "${#PROMPT}" -le 5 ] && exit 0

python3.12 "$FUNGUS_HOME/hooks/memory.py" add \
  --stage spore \
  --hook userPromptSubmit \
  --data "$STDIN"
