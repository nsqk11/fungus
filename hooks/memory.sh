#!/bin/bash
# memory.sh — CRUD operations for memory.json
# Usage: memory.sh <add|delete|list|get|update> [options]
set -euo pipefail

FUNGUS_HOME="${FUNGUS_HOME:-$(cd "$(dirname "$0")/.." && pwd)}"
MEMORY_FILE="$FUNGUS_HOME/data/memory.json"

_ensure() {
  [ -d "$(dirname "$MEMORY_FILE")" ] || mkdir -p "$(dirname "$MEMORY_FILE")"
  [ -f "$MEMORY_FILE" ] || echo '[]' > "$MEMORY_FILE"
}

_write() {
  mv -f "$MEMORY_FILE.tmp" "$MEMORY_FILE"
}

_next_id() {
  local today
  today=$(date -u +%Y%m%d)
  local max
  max=$(jq -r --arg d "$today" \
    '[.[] | select(.id | startswith($d)) | .id[$d | length:] | tonumber] | max // 0' \
    "$MEMORY_FILE")
  printf '%s%03d' "$today" "$((max + 1))"
}

# --- add ---
cmd_add() {
  local stage="" hook="" data="{}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --stage)  stage="$2";  shift 2 ;;
      --hook)   hook="$2";   shift 2 ;;
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
     --argjson data "$data" \
    '. += [{
      id: $id,
      timestamp: $ts,
      stage: $stage,
      hook: $hook,
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
  local stage="" hook=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --stage)  stage="$2";  shift 2 ;;
      --hook)   hook="$2";   shift 2 ;;
      *) echo "Error: unknown option $1" >&2; exit 1 ;;
    esac
  done

  _ensure
  local filter="."
  [ -n "$stage" ]  && filter="$filter | select(.stage == \"$stage\")"
  [ -n "$hook" ]   && filter="$filter | select(.hook == \"$hook\")"

  jq -r ".[] | $filter | \
    \"\\(.id) \\(.stage) \\(.hook)\"" "$MEMORY_FILE"
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

  # Verify ID exists
  local found
  found=$(jq --arg id "$id" '[.[] | select(.id == $id)] | length' "$MEMORY_FILE")
  [ "$found" = "0" ] && { echo "Error: $id not found" >&2; exit 1; }

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

# --- query ---
cmd_query() {
  local filter=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --jq) filter="$2"; shift 2 ;;
      *) echo "Error: unknown option $1" >&2; exit 1 ;;
    esac
  done
  [ -z "$filter" ] && { echo "Error: --jq required" >&2; exit 1; }

  _ensure
  jq -r "$filter" "$MEMORY_FILE"
}

# --- clean ---
cmd_clean() {
  _ensure

  jq '
    [.[] | select(.stage != "skipped" and .stage != "fruiting")] |
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
case "${1:?Usage: memory.sh <add|delete|list|get|update|query|count|clean> [options]}" in
  add)    shift; cmd_add "$@" ;;
  delete) shift; cmd_delete "$@" ;;
  list)   shift; cmd_list "$@" ;;
  get)    shift; cmd_get "$@" ;;
  update) shift; cmd_update "$@" ;;
  query)  shift; cmd_query "$@" ;;
  count)  shift; cmd_count "$@" ;;
  clean)  shift; cmd_clean "$@" ;;
  *)      echo "Error: unknown command $1" >&2; exit 1 ;;
esac
