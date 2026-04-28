#!/bin/bash
# @hook stop
# @priority 10
# @description Finalize current turn, spawn worker async, archive older turns.

set -u

DATA="$FUNGUS_ROOT/data"
MEMORY_FILE="$DATA/long-term-memory.md"
CRITERIA="$FUNGUS_ROOT/prompts/parse-criteria.md"

# Newest turn file, or empty if none exist.
current="$(ls "$DATA"/turn-*.txt 2>/dev/null | sort | tail -n 1)"

# If the newest turn file is not a freshly captured prompt, this
# stop belongs to a turn capture_prompt skipped (e.g. very short
# user input). Do not extend a stale turn; just run archive.
if [ -n "$current" ]; then
  first="$(head -n 1 "$current")"
  case "$first" in
    PROMPT:*) ;;
    *) current="" ;;
  esac
fi

# If there is a fresh current turn, append the response and spawn
# the worker. The worker rewrites the turn file in place: either a
# Markdown memory entry (keep) or an empty file (drop).
if [ -n "$current" ]; then
  payload="$(cat)"
  response="$(printf '%s' "$payload" | python3.12 -c \
    'import json, sys; print(json.load(sys.stdin).get("assistant_response", ""))')"
  printf 'RESPONSE: %s\n' "$response" >> "$current"

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
fi

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
