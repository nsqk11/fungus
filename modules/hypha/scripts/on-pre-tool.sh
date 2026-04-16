#!/bin/bash
# @hook pre-tool-use
# @priority 10
# @module hypha
# @writes spore
# @description Capture tool intent as spore
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

bash "$REPO_ROOT/hooks/memory.sh" add \
  --stage spore \
  --hook pre-tool-use \
  --source agent \
  --data "$STDIN"
