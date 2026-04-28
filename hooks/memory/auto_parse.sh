#!/bin/bash
# @hook stop
# @priority 10
# @description Finalize the turn, run worker, append memory entry, clean up.

set -u

TURN_FILE="$FUNGUS_ROOT/data/current-turn.txt"
MEMORY_FILE="$FUNGUS_ROOT/data/long-term-memory.md"
CRITERIA="$FUNGUS_ROOT/prompts/parse-criteria.md"
OUTPUT_FILE="$FUNGUS_ROOT/data/last-parse-output.md"

# No turn to parse (capture_prompt.py skipped short prompts, or a
# prior stop already cleaned up).
[ -f "$TURN_FILE" ] || exit 0

# Append the assistant response to the turn file.
payload="$(cat)"
response="$(printf '%s' "$payload" | python3.12 -c \
  'import json, sys; print(json.load(sys.stdin).get("assistant_response", ""))')"
printf 'RESPONSE: %s\n' "$response" >> "$TURN_FILE"

# Start from a fresh, empty output file every turn so we never
# confuse a stale file with this turn's result.
: > "$OUTPUT_FILE"

# Build the worker prompt: criteria + turn content + output path.
worker_input="$(cat "$CRITERIA")

---

Turn to evaluate:

$(cat "$TURN_FILE")

---

<output_path> = $OUTPUT_FILE

Write your result to that path now."

# Call the worker synchronously. We ignore its stdout entirely —
# the result is whatever it wrote to $OUTPUT_FILE.
kiro-cli chat --no-interactive --trust-all-tools \
  "$worker_input" > /dev/null 2>&1

# Append the entry only if the worker wrote something.
if [ -s "$OUTPUT_FILE" ]; then
  {
    printf '\n'
    cat "$OUTPUT_FILE"
  } >> "$MEMORY_FILE"
fi

command rm -f -- "$TURN_FILE" "$OUTPUT_FILE"

exit 0
