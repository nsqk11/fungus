#!/bin/bash
# @hook userPromptSubmit
# @priority 5
# @module mycelium
# @writes nutrient
# @description Remind agent to search memory when context is unclear
set -euo pipefail

echo '<memory-reminder>
If anything in the user'\''s message is ambiguous or unclear, search the fungus-memory knowledge base first for relevant context.
</memory-reminder>'
