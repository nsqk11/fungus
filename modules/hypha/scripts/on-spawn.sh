#!/bin/bash
# @hook agentSpawn
# @priority 10
# @module hypha
# @writes none
# @description Remind agent of design-patterns knowledge base
set -euo pipefail

echo '<knowledge-bases-reminder>
Before designing or implementing features, search the design-patterns knowledge base for applicable design patterns. Apply appropriate GoF design patterns.
Before answering questions, search the fungus-memory knowledge base for relevant past decisions, preferences, and lessons learned.
</knowledge-bases-reminder>'
