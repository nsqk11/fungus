#!/bin/bash
# @hook stop
# @priority 10
# @module hypha
# @writes spore
# @description Capture assistant response as spore
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STDIN=$(cat)
[ -z "$STDIN" ] && exit 0

bash "$REPO_ROOT/hooks/memory.sh" add \
  --stage spore \
  --hook stop \
  --source agent \
  --data "$STDIN"
