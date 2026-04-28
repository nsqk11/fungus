---
name: tool-audit
description: "Record every tool call made by the agent and provide statistics on usage patterns and failure rates. Triggered automatically by the postToolUse hook on every tool invocation. Use the CLI to inspect which tools are used most, which fail most, and when. Trigger on mentions of 'tool usage', 'tool stats', 'audit', 'tool failure', 'which tool', or 'tool frequency'. Do NOT use for recording prompt content or agent responses (use memory-curation)."
---

# tool-audit

> Record tool calls. Report usage and failure statistics.

## Boundary

- **Does**:
  - Append one row per tool call via a `postToolUse` hook.
  - Record tool name, timestamp, success flag, and error text.
  - Provide a CLI to query totals, top tools, failure rates, and recent failures.
- **Does not**:
  - Record prompt content, tool input, or agent responses (memory-curation does that).
  - Group calls by session (intentionally out of scope — see README for rationale).
  - Track per-call duration (postToolUse alone cannot measure it reliably).
  - Modify or block tool execution.

## Interface

- **Entry**: `python3.12 scripts/audit.py <command> [args...]`
- **Commands**:
  - `stats` — overall counts, per-tool usage and failure rates.
  - `failures [--last N]` — most recent failures, default 10.
  - `top [--limit N]` — most-used tools, default 10.
- **Data store**: `data/audit.db` (SQLite).
- **Hook**: `scripts/record.py` runs on `postToolUse` and writes one row.

## Behavior

Run `python3.12 scripts/audit.py --help` for command usage.

### What counts as failure

A call is recorded as failed only when `tool_response.success` is explicitly `false` in the hook payload. Other signals (non-zero exit codes inside a successful `execute_bash`, empty results from `fs_read`) are not treated as failures — the tool itself ran, only the work may not have produced what the user wanted.

### Retention

No built-in cap. The table grows indefinitely until pruned manually. For most users this is fine; a year of heavy use is well under a megabyte.
