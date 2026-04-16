#!/bin/bash
# memory.sh — CRUD operations for memory.json
# Usage: memory.sh <add|delete|list|get|update> [options]
set -euo pipefail

FUNGUS_HOME="${FUNGUS_HOME:-$(cd "$(dirname "$0")/.." && pwd)}"
DATA_DIR="$FUNGUS_HOME/data"
MEMORY_FILE="$DATA_DIR/memory.json"

_ensure() {
  mkdir -p "$DATA_DIR"
  [ -f "$MEMORY_FILE" ] || echo '[]' > "$MEMORY_FILE"
}

_write() {
  mv -f "$MEMORY_FILE.tmp" "$MEMORY_FILE"
}

_next_id() {
  local today
  today=$(date -u +%Y%m%d)
  local seq
  seq=$(jq -r --arg d "$today" \
    '[.[] | select(.id | startswith($d))] | length' \
    "$MEMORY_FILE")
  printf '%s%03d' "$today" "$((seq + 1))"
}

# --- add ---
cmd_add() {
  local stage="" hook="" source="" data="{}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --stage)  stage="$2";  shift 2 ;;
      --hook)   hook="$2";   shift 2 ;;
      --source) source="$2"; shift 2 ;;
      --data)   data="$2";   shift 2 ;;
      *) echo "Error: unknown option $1" >&2; exit 1 ;;
    esac
  done
  [ -z "$stage" ] && { echo "Error: --stage required" >&2; exit 1; }

  _ensure
  local id ts
  id=$(_next_id)
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  jq --arg id "$id" \
     --arg ts "$ts" \
     --arg stage "$stage" \
     --arg hook "$hook" \
     --arg source "$source" \
     --argjson data "$data" \
    '. += [{
      id: $id,
      timestamp: $ts,
      stage: $stage,
      hook: $hook,
      source: $source,
      data: $data,
      summary: "",
      keywords: [],
      refs: [],
      category: ""
    }]' "$MEMORY_FILE" > "$MEMORY_FILE.tmp" && _write

  echo "OK: $id"
}

# --- delete ---
cmd_delete() {
  local id="${1:?Error: id required}"
  _ensure

  local before
  before=$(jq 'length' "$MEMORY_FILE")

  jq --arg id "$id" 'map(select(.id != $id))' \
    "$MEMORY_FILE" > "$MEMORY_FILE.tmp" && _write

  local after
  after=$(jq 'length' "$MEMORY_FILE")

  if [ "$before" = "$after" ]; then
    echo "Error: $id not found" >&2
    exit 1
  fi
  echo "OK: deleted $id"
}

# --- get ---
cmd_get() {
  local id="${1:?Error: id required}"
  _ensure
  local result
  result=$(jq --arg id "$id" '.[] | select(.id == $id)' "$MEMORY_FILE")
  if [ -z "$result" ]; then
    echo "Error: $id not found" >&2
    exit 1
  fi
  echo "$result"
}

# --- list ---
cmd_list() {
  local stage="" source="" hook=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --stage)  stage="$2";  shift 2 ;;
      --source) source="$2"; shift 2 ;;
      --hook)   hook="$2";   shift 2 ;;
      *) echo "Error: unknown option $1" >&2; exit 1 ;;
    esac
  done

  _ensure
  local filter="."
  [ -n "$stage" ]  && filter="$filter | select(.stage == \"$stage\")"
  [ -n "$source" ] && filter="$filter | select(.source == \"$source\")"
  [ -n "$hook" ]   && filter="$filter | select(.hook == \"$hook\")"

  jq -r ".[] | $filter | \
    \"\\(.id) \\(.stage) \\(.hook) \\(.source)\"" "$MEMORY_FILE"
}

# --- update ---
cmd_update() {
  local id="" field="" value=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id)    id="$2";    shift 2 ;;
      --field) field="$2"; shift 2 ;;
      --value) value="$2"; shift 2 ;;
      *) echo "Error: unknown option $1" >&2; exit 1 ;;
    esac
  done
  [ -z "$id" ]    && { echo "Error: --id required" >&2; exit 1; }
  [ -z "$field" ] && { echo "Error: --field required" >&2; exit 1; }

  _ensure

  # Detect JSON value vs plain string
  if echo "$value" | jq . >/dev/null 2>&1; then
    jq --arg id "$id" \
       --arg field "$field" \
       --argjson value "$value" \
      'map(if .id == $id then .[$field] = $value else . end)' \
      "$MEMORY_FILE" > "$MEMORY_FILE.tmp" && _write
  else
    jq --arg id "$id" \
       --arg field "$field" \
       --arg value "$value" \
      'map(if .id == $id then .[$field] = $value else . end)' \
      "$MEMORY_FILE" > "$MEMORY_FILE.tmp" && _write
  fi

  echo "OK: $id.$field"
}

# --- clean ---
cmd_clean() {
  _ensure

  # Delete skipped and fruiting entries
  jq '[.[] | select(.stage != "skipped" and .stage != "fruiting")]' \
    "$MEMORY_FILE" > "$MEMORY_FILE.tmp" && _write

  # Cap network at 50, keep newest
  jq '
    ([.[] | select(.stage == "network")] | length) as $n |
    if $n > 50 then
      ([.[] | select(.stage != "network")] +
       ([.[] | select(.stage == "network")] |
        sort_by(.timestamp) | .[-50:]))
    else . end
  ' "$MEMORY_FILE" > "$MEMORY_FILE.tmp" && _write

  echo "OK: clean"
}

# --- count ---
cmd_count() {
  local stage=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --stage) stage="$2"; shift 2 ;;
      *) echo "Error: unknown option $1" >&2; exit 1 ;;
    esac
  done

  _ensure
  if [ -n "$stage" ]; then
    jq --arg s "$stage" '[.[] | select(.stage == $s)] | length' "$MEMORY_FILE"
  else
    jq 'length' "$MEMORY_FILE"
  fi
}

# --- dispatch ---
case "${1:?Usage: memory.sh <add|delete|list|get|update|count|clean> [options]}" in
  add)    shift; cmd_add "$@" ;;
  delete) shift; cmd_delete "$@" ;;
  list)   shift; cmd_list "$@" ;;
  get)    shift; cmd_get "$@" ;;
  update) shift; cmd_update "$@" ;;
  count)  shift; cmd_count "$@" ;;
  clean)  shift; cmd_clean "$@" ;;
  *)      echo "Error: unknown command $1" >&2; exit 1 ;;
esac
