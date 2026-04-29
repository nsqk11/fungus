# project-workbench

A Fungus skill that tracks per-project lifecycle metadata — the stuff
that doesn't live in source files, git history, or memory: deliverable
paths, milestones with blockers, change-log summaries, review comments
with responses, and decision notes.

One JSON file per project. Plain Python 3.12+. No external
dependencies.

## What it is

- A **persistent workbench** that survives across sessions.
- A **metadata-only** store: pointers to your real work, not the work
  itself.
- A **single-user** local CLI, not a collaboration tool.

## What it is not

- A Jira, Linear, or GitHub Issues replacement.
- A todo list (milestones are project-scoped, not daily).
- A place for secrets (plain JSON; no encryption).
- A document store (the source code, spec, or slide deck lives
  elsewhere).

## Requirements

- Python 3.12+
- Nothing else — standard library only.

## Quickstart

```bash
cd skills/project-workbench

# Create a workbench for a new project
python3.12 scripts/cli.py init my-proj --name "Q2 design refresh" --type feature

# Track a deliverable path (edit the JSON or write a note for now)
python3.12 scripts/cli.py note my-proj --topic "Files" \
  --content "Design doc: ~/work/my-proj/design.md"

# Record progress
python3.12 scripts/cli.py milestone add my-proj --name "Kickoff" --target 2026-05-02
python3.12 scripts/cli.py log my-proj --summary "First draft of Section 1"
python3.12 scripts/cli.py review add my-proj --comment "Rephrase heading" --by "Alex"

# See what's pending
python3.12 scripts/cli.py status my-proj
python3.12 scripts/cli.py remind
```

## Commands

Run `python3.12 scripts/cli.py <command> --help` for flags.

| Command                         | Purpose                                           |
|---------------------------------|---------------------------------------------------|
| `init <id>`                     | Create a new workbench                            |
| `query <id>`                    | Print workbench JSON or a sub-field               |
| `log <id>`                      | Append a one-line change-log entry                |
| `review add <id>`               | Record a review comment                           |
| `review done <id>`              | Mark a review comment resolved                    |
| `milestone add <id>`            | Add a milestone                                   |
| `milestone done <id>`           | Mark a milestone complete                         |
| `milestone update <id>`         | Move a milestone target or note                   |
| `note <id>`                     | Add a decision note                               |
| `status <id>`                   | Show pending milestones and open reviews          |
| `list`                          | List every workbench, with `--status` filter      |
| `remind`                        | Pending items across all `active` workbenches     |
| `archive <id>`                  | Hide the workbench from default listings          |
| `done <id>`                     | Mark the workbench complete                       |

`<id>` accepts any unique prefix after `init`.

## Storage

Default path:

```
skills/project-workbench/data/workbenches/<id>.json
```

Override with `PROJECT_WORKBENCH_DIR=/absolute/path` — useful for
placing workbenches under a Dropbox / iCloud / git-tracked directory.

Data shape is documented in [`references/schema.md`](references/schema.md).

## Design decisions

- **One JSON file per project.** Single-user, low write frequency, and
  human-readable storage all favour plain JSON over SQLite or a KV
  store.
- **Atomic writes.** Every `cli.py` write goes through
  `os.replace(tmp, target)` on a sibling file to survive crashes
  mid-write.
- **Prefix-match IDs.** Full IDs can be long; any unique prefix works
  after `init`. Ambiguous prefixes error out with the candidates.
- **No schema migration engine.** Schema shifts are rare; when they
  happen, a one-shot script outside the skill handles the upgrade.
- **Manual `remind`, not an auto hook.** Agent-start reminders noise
  up most sessions. The `SKILL.md` includes a snippet users can drop
  in if they want automatic injection.
- **No encryption, no secrets.** If you need a PAT or password, store
  it elsewhere (e.g. the `atlassian-api` skill) and put only a
  reference here.

## Scope boundary

- Does not sync to external PM tools.
- Does not render Markdown or produce reports; `query` prints raw JSON
  for the agent or another tool to format.
- Does not expire old data. `archive` hides a workbench from listings;
  pruning is manual (`rm skills/project-workbench/data/workbenches/<id>.json`).

## License

Same as the parent repository (see repository root `LICENSE`).
