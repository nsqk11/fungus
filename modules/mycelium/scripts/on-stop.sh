#!/bin/bash
# @hook stop
# @priority 90
# @module mycelium
# @description Export nutrient + network to memory.md for KB indexing
set -euo pipefail

python3.12 "$FUNGUS_HOME/modules/mycelium/scripts/export-kb.py" >/dev/null 2>&1
