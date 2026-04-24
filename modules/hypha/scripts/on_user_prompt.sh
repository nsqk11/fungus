#!/bin/bash
# @hook userPromptSubmit
# @priority 10
# @module hypha
# @writes spore
# @description Capture user prompt as spore
set -euo pipefail

stdin=$(cat)
[ -z "$stdin" ] && exit 0

# Drop trivial prompts (≤ 5 characters)
prompt=$(printf '%s' "$stdin" | python3.12 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))")
[ "${#prompt}" -le 5 ] && exit 0

python3.12 "$FUNGUS_HOME/hooks/memory.py" add \
  --stage spore \
  --hook userPromptSubmit \
  --data "$stdin"
