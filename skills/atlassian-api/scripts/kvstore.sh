#!/usr/bin/env bash
# Generic JSON key-value store
# Usage:
#   kvstore.sh <file> get <key>
#   kvstore.sh <file> set <key> <value>
#   kvstore.sh <file> remove <key>
#   kvstore.sh <file> list
#   kvstore.sh <file> search <keyword>     — fuzzy match on values (all words must match)
set -euo pipefail

FILE="${1:-}"; CMD="${2:-}"; KEY="${3:-}"; VAL="${4:-}"
[[ -n "$FILE" && -n "$CMD" ]] || { echo "Usage: kvstore.sh <file> {get|set|remove|list|search} [key] [value]" >&2; exit 1; }
[[ -f "$FILE" ]] || echo '{}' > "$FILE"

case "$CMD" in
  get)    jq -r --arg k "$KEY" '.[$k] // empty' "$FILE" ;;
  set)    jq --arg k "$KEY" --arg v "$VAL" '.[$k]=$v' "$FILE" > "$FILE.tmp" && mv -f "$FILE.tmp" "$FILE" ;;
  remove) jq --arg k "$KEY" 'del(.[$k])' "$FILE" > "$FILE.tmp" && mv -f "$FILE.tmp" "$FILE" ;;
  list)   jq -r 'keys[]' "$FILE" ;;
  search) jq -r --arg q "${KEY}" 'to_entries[] | select((.value | ascii_downcase) as $v | ($q | ascii_downcase | split(" ") | all(. as $w | $v | contains($w)))) | "\(.key)  \(.value)"' "$FILE" ;;
  *)      echo "Unknown command: $CMD" >&2; exit 1 ;;
esac
