---
name: task-tracking
description: "Records progress and history for any ongoing task. Use whenever the user starts a task, logs progress, records a decision, tracks a deliverable, or asks what happened on a task. Also use when the user mentions milestones, blockers, deliverables, or wants a status summary. Think of it as a structured logbook — one database, many tasks, append-mostly."
compatibility: "Python 3.10+"
---

# Task Tracking

A structured logbook for tasks. One SQLite database, one row per
record. Each record belongs to a task and has a type and content.

## Schema

```sql
CREATE TABLE records (
    id         INTEGER PRIMARY KEY,  -- nanosecond timestamp (= creation time)
    task_id    TEXT NOT NULL,         -- user-assigned identifier (e.g. "915-SP1")
    type       TEXT NOT NULL,         -- record type (see below)
    content    TEXT NOT NULL,         -- free-text body
    updated_at TEXT NOT NULL          -- ISO-8601 UTC, refreshed on every write
);

CREATE INDEX idx_task ON records(task_id);
CREATE INDEX idx_type ON records(task_id, type);
```

### Record types

Types are free-form strings. Recommended conventions:

| Type | Use for |
|------|---------|
| `meta` | Task name, status (active/done/archived) |
| `milestone` | Deadline or checkpoint |
| `log` | What changed today |
| `deliverable` | Where an output file lives |
| `reference` | Where an input/dependency lives |
| `review` | Review comment + response |
| `note` | Decision rationale, design choice |
| `blocker` | What's blocking progress |

Types are not enforced — use any string that makes sense.

## CLI

```
scripts/cli.py <command> [args...]
```

### Write commands

```
scripts/cli.py init <task_id> --name NAME
scripts/cli.py add <task_id> --type TYPE --content TEXT
scripts/cli.py update <id> [--content TEXT] [--type TYPE]
scripts/cli.py delete <id>
scripts/cli.py done <task_id>
scripts/cli.py archive <task_id>
```

- `init`: creates a `meta` record with content = NAME, status = active.
- `add`: appends a new record. Returns the generated id.
- `update`: modifies an existing record by id. Refreshes `updated_at`.
- `delete`: removes a record by id.
- `done` / `archive`: shorthand for updating the `meta` record's content to include status.

### Read commands

```
scripts/cli.py get <task_id> [--type TYPE] [--last N] [--since DATE]
scripts/cli.py show <id>
scripts/cli.py list [--status STATUS]
scripts/cli.py status <task_id>
scripts/cli.py remind
scripts/cli.py search --query TEXT [--task_id ID] [--type TYPE]
```

- `get`: list records for a task. Filter by type, limit by count or date.
- `show`: print a single record by id.
- `list`: list all tasks (shows the `meta` record for each).
- `status`: summary — pending milestones, recent logs, open blockers.
- `remind`: pending items across all active tasks.
- `search`: full-text search across content.

## Examples

**Start a task:**
```
$ scripts/cli.py init 915-SP1 --name "CT-50 HW Platform Migration"
OK: created 915-SP1 (id: 1716700800000000000)
```

**Add records:**
```
$ scripts/cli.py add 915-SP1 --type milestone --content "1/3 Review target: 2025-W08"
OK: added (id: 1716700801000000000)

$ scripts/cli.py add 915-SP1 --type log --content "Completed Ch4.1 HW architecture section"
OK: added (id: 1716700802000000000)

$ scripts/cli.py add 915-SP1 --type deliverable --content "NDS Report: ~/Documents/remote/915-SP1/NDS.docx"
OK: added (id: 1716700803000000000)

$ scripts/cli.py add 915-SP1 --type review --content "TC-Lars: Missing sequence diagram in 4.1.1.4"
OK: added (id: 1716700804000000000)
```

**Query records:**
```
$ scripts/cli.py get 915-SP1 --type milestone
1716700801000000000  milestone  1/3 Review target: 2025-W08  (2025-01-26T10:00:00Z)

$ scripts/cli.py get 915-SP1 --last 3
1716700804000000000  review       TC-Lars: Missing sequence diagram...
1716700803000000000  deliverable  NDS Report: ~/Documents/remote/...
1716700802000000000  log          Completed Ch4.1 HW architecture...
```

**Update a record:**
```
$ scripts/cli.py update 1716700804000000000 --content "TC-Lars: Missing sequence diagram in 4.1.1.4 [RESOLVED: added in v3]"
OK: updated
```

**Status summary:**
```
$ scripts/cli.py status 915-SP1
=== 915-SP1: CT-50 HW Platform Migration (active) ===
Milestones: 1
  • 1/3 Review target: 2025-W08
Recent (last 3):
  • [log] Completed Ch4.1 HW architecture section
  • [deliverable] NDS Report: ~/Documents/remote/915-SP1/NDS.docx
  • [review] TC-Lars: Missing sequence diagram in 4.1.1.4 [RESOLVED]
```

**List all tasks:**
```
$ scripts/cli.py list
915-SP1   active    CT-50 HW Platform Migration
865-OA1   done      CSIM FsUE NR Feature Merge
```

**Search:**
```
$ scripts/cli.py search --query "sequence diagram"
[915-SP1] 1716700804000000000  review  TC-Lars: Missing sequence diagram...
```

## Error handling

All errors print to stderr with `ERROR:` prefix and exit code 1.

| Situation | Message |
|-----------|---------|
| Task not found | `no task matching '<id>'` |
| Record id not found | `record <id> not found` |
| Task already exists | `task '<id>' already exists` |

## Storage

SQLite at `$KIRO_HOME/data/task-tracking/tasks.db`.
Override with `TASK_TRACKING_DB` env var.

## Design principles

- **Append-mostly**: prefer adding new records over modifying old ones.
- **Free-form content**: no rigid structure inside content — just text.
- **Types are conventions**: the CLI doesn't enforce what types mean.
- **Agent-friendly**: simple commands, predictable output format.
