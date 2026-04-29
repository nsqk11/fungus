---
name: project-workbench
description: "Per-project workbench that tracks lifecycle metadata kept outside source files: deliverable and reference paths, milestones with blockers, change log summaries, review comments with responses, and decision notes. Use when starting a new project, looking up a project's file paths or URLs, recording what was just changed, tracking review comments, checking what is blocking progress, or capturing the reasoning behind a decision for later defence. Trigger on: 'workbench', 'milestone', 'blocker', 'change log', 'review comment', 'decision note', 'project status', 'what did I change', 'where is the file for'. Do NOT use for source content itself (code, specs, slides), real-time collaboration (Jira, Linear, GitHub Issues), or syncing with external PM tools."
---

# project-workbench

One JSON file per project under ``data/workbenches/<id>.json``. Stores
the lifecycle metadata that source files, git history, and memory do
not: resource paths, milestones with blockers, change log summaries,
review comments, and decision notes.

## Scope

- **Does**
  - Maintain a per-project index of deliverables (what you are
    producing) and references (what you are consuming).
  - Track milestones with target dates and blocker notes.
  - Record one-line change log entries with optional git-sha / PR refs.
  - Capture review comments, who raised them, and your response.
  - Store decision notes (why you chose X over Y) so you can defend
    them later.
  - Surface pending milestones and open review comments on demand via
    ``status`` and ``remind``.
- **Does not**
  - Store source content. The source code, spec, or document itself
    lives elsewhere; this skill stores pointers and metadata only.
  - Sync with Jira, Linear, GitHub Issues, or any other PM tool. It is
    a local JSON store by design.
  - Replace a todo list. Milestones are project-scoped lifecycle
    markers, not daily tasks.
  - Encrypt data. Do not write secrets into workbench fields.

## Entry points

Run from the skill directory (path shown from the repo root):

```
python3.12 skills/project-workbench/scripts/cli.py <command> [args...]
python3.12 skills/project-workbench/scripts/cli.py --help
python3.12 skills/project-workbench/scripts/cli.py <command> --help
```

Commands:

```
init      <id> --name NAME [--type TYPE]
query     <id> [--field PATH]
log       <id> --summary TEXT [--date YYYY-MM-DD] [--ref REF]
review    add  <id> --comment TEXT --by WHO [--location LOC] [--response TEXT]
review    done <id> --review-id N [--response TEXT]
milestone add    <id> --name NAME [--target T] [--note N]
milestone done   <id> --name NAME [--note N]
milestone update <id> --name NAME [--target T] [--note N]
note      <id> --topic T --content C
status    <id>
list      [--status active|paused|done|archived]
remind
archive   <id>
done      <id>
```

``<id>`` accepts any unique prefix after ``init``. A typo-prone full
ID like ``my-project-2026-q2`` only needs enough prefix to be
unambiguous.

## When to use

| User intent / cue                                  | Command                          |
|----------------------------------------------------|----------------------------------|
| "Starting a new project / study / feature"         | ``init``                         |
| "Where did I put the spec / slides / PR?"          | ``query --field deliverables``   |
| "I just updated the design doc"                    | ``log --summary "..."``          |
| "Reviewer X said Y in today's review"              | ``review add``                   |
| "I fixed the issue the reviewer raised"            | ``review done --response "..."`` |
| "Move the Final Review date"                       | ``milestone update --target T``  |
| "Record why I chose approach A"                    | ``note --topic ... --content ...``|
| "What's blocking this project"                     | ``status``                       |
| "What projects are active and what's pending"      | ``remind``                       |
| "Shelve this project, might come back to it"       | ``archive``                      |
| "This project is done, keep it for reference"      | ``done``                         |

## Field reference

See ``references/schema.md`` for the full JSON shape and per-field
rules. Read it before composing a query that targets nested fields.

## Storage

- Default location: ``skills/project-workbench/data/workbenches/<id>.json``.
- Override by setting ``PROJECT_WORKBENCH_DIR`` to an absolute path.
- Each write is atomic (``os.replace`` via a sibling temp file). Safe
  to interrupt.
- ``createdAt`` is set on ``init``; ``updatedAt`` is refreshed on every
  write. Both are UTC ISO-8601.

## Not a skill to advertise

This skill does not teach the user about project management. It is a
silent backing store that accumulates metadata across sessions. Do not
recite its capabilities to the user unless asked; just use it.

## Automatic reminders (opt-in)

``remind`` is intentionally a manual command. If the user wants its
output injected at agent startup, add a small hook script in this
skill's ``scripts/`` directory:

```python
# scripts/_remind_on_spawn.py
# @hook agentSpawn
# @priority 10
# @skill project-workbench
# @description Inject pending items from every active workbench.

import subprocess, sys
from pathlib import Path

cli = Path(__file__).resolve().parent / "cli.py"
r = subprocess.run(
    ["python3.12", str(cli), "remind"],
    capture_output=True, text=True, check=False,
)
if r.stdout.strip():
    sys.stdout.write("<workbench-reminder>\n")
    sys.stdout.write(r.stdout)
    sys.stdout.write("</workbench-reminder>\n")
```

Do not add this by default; inject it only when the user asks.
