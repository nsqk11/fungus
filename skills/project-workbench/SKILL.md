---
name: project-workbench
description: "Per-project workbench that tracks lifecycle metadata kept outside source files: deliverable and reference paths, milestones with blockers, change log summaries, review comments with responses, and decision notes. Use when starting a new project, looking up a project's file paths or URLs, recording what was just changed, tracking review comments, checking what is blocking progress, or capturing the reasoning behind a decision for later defence. Trigger on: 'workbench', 'milestone', 'blocker', 'change log', 'review comment', 'decision note', 'project status', 'what did I change', 'where is the file for', '项目进度', '交付物', '评审意见', '里程碑', '记录一下改了什么', '文件放哪了'. Do NOT use for source content itself (code, specs, slides), real-time collaboration (Jira, Linear, GitHub Issues), or syncing with external PM tools."
---

# project-workbench

One JSON file per project under `data/workbenches/<id>.json`. Stores
lifecycle metadata that source files, git history, and memory do not
cover: resource paths, milestones, change log, review comments, and
decision notes.

## Scope

**Does:** maintain deliverable/reference paths, milestones with
blockers, one-line change log entries, review comments with responses,
decision notes, and surface pending items via `status`/`remind`.

**Does not:** store source content (only pointers), sync with external
PM tools, replace a todo list, or handle secrets.

## CLI

```
python3.12 skills/project-workbench/scripts/cli.py <command> [args...]
```

`<id>` accepts any unique prefix after `init`.

| Command | Purpose |
|---------|---------|
| `init <id> --name NAME [--type T]` | Create workbench |
| `query <id> [--field PATH]` | Print data (dot-path into JSON) |
| `deliverable add <id> --label L [--type T] [--path P\|--url U]` | Register an output |
| `deliverable rm <id> --label L` | Remove a deliverable |
| `reference add <id> --label L [--type T] [--path P\|--url U]` | Register an input |
| `reference rm <id> --label L` | Remove a reference |
| `log <id> --summary TEXT [--date D] [--ref R]` | Append change log entry |
| `review add <id> --comment C --by WHO [--location L] [--response R]` | Record review comment |
| `review done <id> --review-id N [--response R]` | Close a review comment |
| `milestone add <id> --name N [--target T] [--note N]` | Add milestone |
| `milestone done <id> --name N [--note N]` | Mark milestone done |
| `milestone update <id> --name N [--target T] [--note N]` | Update target/note |
| `note <id> --topic T --content C` | Add decision note |
| `status <id>` | Pending milestones + open reviews |
| `list [--status S]` | List workbenches |
| `remind` | Pending items across all active workbenches |
| `archive <id>` / `done <id>` | Change status |

## When to use

| User intent | Command |
|-------------|---------|
| Starting a new project/study | `init` |
| Registering a deliverable or reference | `deliverable add` / `reference add` |
| "Where is the spec/slides/PR?" | `query --field deliverables` |
| "I just updated the design doc" | `log` |
| "Reviewer X said Y" | `review add` |
| "Fixed the reviewer's issue" | `review done` |
| "Move the Final Review date" | `milestone update` |
| "Record why I chose approach A" | `note` |
| "What's blocking this project" | `status` |
| "What's pending across projects" | `remind` |
| "Shelve / finish this project" | `archive` / `done` |

## Schema

See `references/schema.md` for the full JSON shape and per-field rules.

## Storage

Default: `skills/project-workbench/data/workbenches/<id>.json`.
Override: set `PROJECT_WORKBENCH_DIR`. Writes are atomic via
`os.replace`. Timestamps are UTC ISO-8601.

## Behaviour

This is a silent backing store. Do not advertise capabilities unless
asked — just use it when the context matches.
