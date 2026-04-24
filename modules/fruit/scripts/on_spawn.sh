#!/bin/bash
# @hook agentSpawn
# @priority 30
# @module fruit
# @writes fruiting
# @description Remind about mature nutrient patterns
set -euo pipefail

memory() {
  python3.12 "$FUNGUS_HOME/hooks/memory.py" "$@"
}

# Check for nutrients
count=$(memory count --stage nutrient)
[ "$count" = "0" ] && exit 0

# Extract keyword frequencies across all nutrients
keywords=$(memory query --sql \
  "SELECT keywords FROM memory WHERE stage='nutrient' AND keywords != '[]'" \
  | python3.12 -c "
import sys, json
from collections import Counter
counts = Counter()
for line in sys.stdin:
    for kw in json.loads(line.strip()):
        counts[kw] += 1
top = counts.most_common(10)
print(', '.join(f'{c}x {k}' for k, c in top))
")

echo "<fruit-reminder>"
echo "$count nutrients accumulated."
[ -n "$keywords" ] && echo "Top keywords: $keywords"
echo "Ask the user if they want to review for skill emergence."
echo "If confirmed, read modules/fruit/SKILL.md for instructions."
echo "</fruit-reminder>"
