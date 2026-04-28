#!/bin/bash
# @hook stop
# @priority 10
# @description Finalize the turn, run worker, append memory entry, clean up.

set -u

TURN_FILE="$FUNGUS_ROOT/data/current-turn.txt"
MEMORY_FILE="$FUNGUS_ROOT/data/long-term-memory.md"
CRITERIA="$FUNGUS_ROOT/prompts/parse-criteria.md"
BEGIN_MARK="<<<FUNGUS_MEMORY_BEGIN>>>"
END_MARK="<<<FUNGUS_MEMORY_END>>>"

# No turn to parse (capture_prompt.py skipped short prompts, or a
# prior stop already cleaned up).
[ -f "$TURN_FILE" ] || exit 0

# Read the hook payload from stdin and append the assistant response.
payload="$(cat)"
response="$(printf '%s' "$payload" | python3.12 -c \
  'import json, sys; print(json.load(sys.stdin).get("assistant_response", ""))')"
printf 'RESPONSE: %s\n' "$response" >> "$TURN_FILE"

# Build the worker prompt: criteria + turn content.
worker_input="$(cat "$CRITERIA")

---

Turn to evaluate:

$(cat "$TURN_FILE")"

# Call the worker synchronously. Captures both stdout and stderr;
# sentinel markers isolate the entry from any UI noise.
worker_output="$(kiro-cli chat --no-interactive --trust-all-tools \
  "$worker_input" 2>&1)"

entry="$(printf '%s' "$worker_output" \
  | sed -n "/$BEGIN_MARK/,/$END_MARK/p" \
  | sed '1d;$d')"

# Trim leading/trailing blank lines.
entry="$(printf '%s' "$entry" | awk 'NF {p=1} p')"

if [ -n "$entry" ]; then
  {
    printf '\n'
    printf '%s\n' "$entry"
  } >> "$MEMORY_FILE"
fi

# Clean up scratch. Worker I/O stayed in shell variables.
command rm -f -- "$TURN_FILE"

exit 0
