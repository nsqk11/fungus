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

# Only capture tool failures
SUCCESS=$(printf '%s' "$STDIN" | python3.12 -c "import sys,json; r=json.load(sys.stdin).get('tool_response',{}); print(r.get('success','true') if isinstance(r,dict) else 'true')")
[ "$SUCCESS" != "false" ] && exit 0

python3.12 "$FUNGUS_HOME/hooks/memory.py" add \
  --stage spore \
  --hook postToolUse \
  --data "$STDIN"
