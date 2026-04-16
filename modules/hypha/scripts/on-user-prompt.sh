#!/bin/bash
# @hook user-prompt-submit
# @priority 10
# @module hypha
# @writes spore
# @description Capture user prompt as spore
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

bash "$REPO_ROOT/hooks/memory.sh" add \
  --stage spore \
  --hook user-prompt-submit \
  --source user \
  --data "$STDIN"
