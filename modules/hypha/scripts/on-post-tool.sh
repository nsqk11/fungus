#!/bin/bash
# @hook postToolUse
# @priority 10
# @module hypha
# @writes spore
# @description Capture tool result as spore
set -euo pipefail

STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

# Skip self-referential calls (auditd pattern: exclude own operations)
printf '%s' "$STDIN" | grep -q 'memory\.sh' && exit 0

bash "$FUNGUS_HOME/hooks/memory.sh" add \
  --stage spore \
  --hook postToolUse \
  --source environment \
  --data "$STDIN"
