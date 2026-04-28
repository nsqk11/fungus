#!/bin/bash
# @hook stop
# @priority 10
# @description Finalize current turn, spawn worker async, archive older turns.

set -u

DATA="$FUNGUS_ROOT/data"
MEMORY_FILE="$DATA/long-term-memory.md"
CRITERIA="$FUNGUS_ROOT/prompts/parse-criteria.md"

# Locate the current turn file (lexicographic max over turn-*.txt).
current=""
for f in "$DATA"/turn-*.txt; do
  [ -e "$f" ] && current="$f"
done

[ -n "$current" ] || exit 0

# Append the assistant response to the current turn file.
payload="$(cat)"
response="$(printf '%s' "$payload" | python3.12 -c \
  'import json, sys; print(json.load(sys.stdin).get("assistant_response", ""))')"
printf 'RESPONSE: %s\n' "$response" >> "$current"

# Spawn the worker in the background.
# It reads the turn file and rewrites it in place: either a
# Markdown memory entry (keep) or an empty file (drop).
worker_prompt="$(cat "$CRITERIA")

---

Read the turn data from: $current
Write your result back to the same path.
"
(
  kiro-cli chat --no-interactive --trust-all-tools \
    "$worker_prompt" > /dev/null 2>&1
) &
disown

# Archive any non-current turn files whose worker already finished.
for f in "$DATA"/turn-*.txt; do
  [ -e "$f" ] || continue
  [ "$f" = "$current" ] && continue

  if [ ! -s "$f" ]; then
    # Worker chose drop (empty file).
    command rm -f -- "$f"
    continue
  fi

  # If the file still starts with "PROMPT:", the worker hasn't
  # finished yet. Leave it for the next stop.
  first="$(head -n 1 "$f")"
  case "$first" in
    PROMPT:*) continue ;;
  esac

  # Otherwise the worker has rewritten it into a memory entry.
  {
    printf '\n'
    cat "$f"
  } >> "$MEMORY_FILE"
  command rm -f -- "$f"
done

exit 0
