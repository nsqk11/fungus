#!/bin/bash
# @hook stop
# @priority 10
# @description Apply pending distill, finalize current turn, archive, trigger distill.

set -u

DATA="$FUNGUS_ROOT/data"
MEMORY_FILE="$DATA/long-term-memory.md"
MEMORY_LOCK="$DATA/.memory.lock"
EXTRACT_CRITERIA="$FUNGUS_ROOT/prompts/parse-criteria.md"
DISTILL_CRITERIA="$FUNGUS_ROOT/prompts/distill-criteria.md"
DISTILL_THRESHOLD=200
SID="${KIRO_SESSION_ID:-default}"

# -------- Phase 1: apply pending distill --------
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
      tail -c "+$((snap_size + 1))" "$MEMORY_FILE" >> "$tmp"
    fi
    (
      flock 9
      mv "$tmp" "$MEMORY_FILE"
    ) 9>"$MEMORY_LOCK"
    command rm -f -- "$distilled" "$snapshot"
  fi
fi

# -------- Phase 2: finalize current turn --------
# Only look at turn files belonging to this session.
current="$(ls "$DATA"/turn-"$SID"-*.txt 2>/dev/null | sort | tail -n 1)"

if [ -n "$current" ]; then
  first="$(head -n 1 "$current")"
  case "$first" in
    PROMPT:*) ;;
    *) current="" ;;
  esac
fi

payload="$(cat)"

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
# Only process turn files belonging to this session.
for f in "$DATA"/turn-"$SID"-*.txt; do
  [ -e "$f" ] || continue
  [ "$f" = "$current" ] && continue

  if [ ! -s "$f" ]; then
    command rm -f -- "$f"
    continue
  fi

  first="$(head -n 1 "$f")"
  case "$first" in
    PROMPT:*)
      if [ "$(find "$f" -mmin +1440 2>/dev/null)" ]; then
        command rm -f -- "$f"
      fi
      continue ;;
  esac

  # Append to memory with flock.
  (
    flock 9
    printf '\n' >> "$MEMORY_FILE"
    cat "$f" >> "$MEMORY_FILE"
  ) 9>"$MEMORY_LOCK"
  command rm -f -- "$f"
done

# -------- Phase 4: trigger distill worker --------
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
