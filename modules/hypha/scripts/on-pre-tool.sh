#!/bin/bash
# @hook preToolUse
# @priority 10
# @module hypha
# @writes spore
# @description Capture tool intent as spore
set -euo pipefail

STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

# Skip self-referential calls (auditd pattern: exclude own operations)
printf '%s' "$STDIN" | grep -q 'memory\.sh' && exit 0

# Skip pure read/write and internal management tools
TOOL=$(printf '%s' "$STDIN" | python3.12 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))")
case "$TOOL" in fs_read|grep|glob|code|todo_list) exit 0 ;; esac

# Remind agent to follow Google Style Guide before writing files
if [ "$TOOL" = "fs_write" ]; then
  echo '<knowledge-bases-reminder>
Before writing code, search the google-styleguide knowledge base for the relevant language style rules. Apply Google Style Guide conventions.
Before writing SKILL.md files, search the agent-skills-spec knowledge base for the official format specification.
</knowledge-bases-reminder>'
  exit 0
fi

python3.12 "$FUNGUS_HOME/hooks/memory.py" add \
  --stage spore \
  --hook preToolUse \
  --data "$STDIN"
