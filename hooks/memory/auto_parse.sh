#!/bin/bash
# @hook stop
# @priority 10
# @description Apply pending distill, finalize current turn, archive, trigger distill.

set -u

DATA="$FUNGUS_ROOT/data"
MEMORY_FILE="$DATA/long-term-memory.md"
EXTRACT_CRITERIA="$FUNGUS_ROOT/prompts/parse-criteria.md"
DISTILL_CRITERIA="$FUNGUS_ROOT/prompts/distill-criteria.md"
DISTILL_THRESHOLD=200

# -------- Phase 1: apply pending distill --------
#
# If a distill worker produced a (memory-<ts>.md, memory-<ts>.snapshot.md)
# pair, replace the main file with the distilled content plus any tail
# appended since the worker took its snapshot. The main file is
# append-only, so the tail is exactly the bytes beyond the snapshot's
# length.
apply_pair="$(ls "$DATA"/memory-*.snapshot.md 2>/dev/null | sort | tail -n 1)"
if [ -n "$apply_pair" ]; then
  snapshot="$apply_pair"
  distilled="${apply_pair%.snapshot.md}.md"

  if [ -s "$distilled" ] && [ -f "$MEMORY_FILE" ]; then
    snap_size=$(wc -c < "$snapshot")
    main_size=$(wc -c < "$MEMORY_FILE")

    tmp="$MEMORY_FILE.tmp.$$"
    cp "$distilled" "$tmp"
    if [ "$main_size" -gt "$snap_size" ]; then
      # Append the tail: bytes written to main after the snapshot.
      tail -c "+$((snap_size + 1))" "$MEMORY_FILE" >> "$tmp"
    fi
    mv "$tmp" "$MEMORY_FILE"
    command rm -f -- "$distilled" "$snapshot"
  else
    # Distilled file missing or empty — worker failed or still running.
    # Leave the snapshot in place; a later stop will retry.
    :
  fi
fi

# -------- Phase 2: finalize current turn --------
#
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

# Read hook payload from stdin once; phase 2 needs the response,
# and later phases do not reread it.
payload="$(cat)"

# If there is a fresh current turn, append the response and spawn
# the extract worker. The worker rewrites the turn file in place:
# either a Markdown memory entry (keep) or an empty file (drop).
if [ -n "$current" ]; then
  response="$(printf '%s' "$payload" | python3.12 -c \
    'import json, sys; print(json.load(sys.stdin).get("assistant_response", ""))')"
  printf 'RESPONSE: %s\n' "$response" >> "$current"

  extract_prompt="$(cat "$EXTRACT_CRITERIA")

---

Read the turn data from: $current
Write your result back to the same path.
"
  (
    kiro-cli chat --no-interactive --trust-all-tools \
      "$extract_prompt" > /dev/null 2>&1
  ) &
  disown
fi

# -------- Phase 3: archive finished turn files --------
#
# Any non-current turn file whose extract worker has finished is
# either empty (drop) or starts with a Markdown heading (keep).
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

# -------- Phase 4: trigger distill worker --------
#
# Count memory entries (lines starting with "## "). If the count
# exceeds the threshold and no distill is already pending, snapshot
# the current main file and spawn a detached worker to produce a
# distilled replacement. Phase 1 on a future stop will apply it.
if [ -f "$MEMORY_FILE" ]; then
  pending="$(ls "$DATA"/memory-*.snapshot.md 2>/dev/null | head -n 1)"
  if [ -z "$pending" ]; then
    entry_count="$(grep -c '^## ' "$MEMORY_FILE" 2>/dev/null || echo 0)"
    if [ "$entry_count" -gt "$DISTILL_THRESHOLD" ]; then
      ts="$(date +%s%N)"
      snapshot="$DATA/memory-$ts.snapshot.md"
      distilled="$DATA/memory-$ts.md"

      cp "$MEMORY_FILE" "$snapshot"

      distill_prompt="$(cat "$DISTILL_CRITERIA")

---

Read the memory store from: $snapshot
Write the distilled store to: $distilled
"
      (
        kiro-cli chat --no-interactive --trust-all-tools \
          "$distill_prompt" > /dev/null 2>&1
      ) &
      disown
    fi
  fi
fi

exit 0
