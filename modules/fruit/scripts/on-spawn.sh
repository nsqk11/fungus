#!/bin/bash
# @hook agentSpawn
# @priority 30
# @module fruit
# @writes fruiting
# @description Remind about mature nutrient patterns
set -euo pipefail

MEMORY="$FUNGUS_HOME/hooks/memory.sh"

# Check for nutrients
count=$(bash "$MEMORY" count --stage nutrient)
[ "$count" = "0" ] && exit 0

# Extract keyword frequencies across all nutrients
keywords=$(bash "$MEMORY" query --jq '
  [.[] | select(.stage == "nutrient") | .keywords[]?] |
  group_by(.) | map({key: .[0], count: length}) |
  sort_by(-.count) | .[0:10] |
  map("\(.count)x \(.key)") | join(", ")
')

echo "<fruit-reminder>"
echo "$count nutrients accumulated."
[ -n "$keywords" ] && echo "Top keywords: $keywords"
echo "Ask the user if they want to review for skill emergence."
echo "If confirmed, read modules/fruit/SKILL.md for instructions."
echo "</fruit-reminder>"
