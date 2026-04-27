# Pattern Protocol

Operating manual for detecting patterns in `parsed` entries and
growing them into new skills. Invoked when a
`<memory-curation-reminder>` reports accumulated patterns at session
start.

## Storage Commands

List parsed entries:

```bash
python3.12 scripts/memory.py list --stage parsed
```

Get entry detail:

```bash
python3.12 scripts/memory.py get <id>
```

Promote entry to `longterm` (permanent memory):

```bash
python3.12 scripts/memory.py update --id <id> --field stage --value longterm
python3.12 scripts/memory.py update --id <id> --field category --value "<category>"
```

Drop a valueless entry:

```bash
python3.12 scripts/memory.py update --id <id> --field stage --value dropped
```

## Pattern Detection

Review all `parsed` entries. Classify each:

- **Recurring keyword** — the same keyword appears in 3 or more
  entries. The underlying topic is worth capturing as a skill.
- **Single insight** — a standalone fact with no recurring pattern.
  Promote to `longterm` with an appropriate `category`.
- **No pattern** — skip silently; the entry stays in `parsed` until a
  future pass.

When a recurring pattern is found, confirm with the user before
proceeding to Skill Creation.

## Skill Creation

When a pattern matures into a skill, capture intent from the user,
then hand off to writing. This protocol ends at the handoff; it does
not prescribe how to write the skill.

### 1. Capture intent

Clarify with the user:

- What should this skill enable the agent to do?
- When should it trigger? (phrases, contexts, file types)
- What is explicitly out of scope?

Extract answers from the `parsed` entries where possible. The user
fills gaps and confirms before proceeding.

### 2. Hand off to writing

Produce a short intent summary covering the three questions above,
and hand it to the writing step. The new `SKILL.md` is authored
following the project's writing standards. This protocol stops here.

### 3. Update entry stages

After the new skill is written and accepted:

- Entries that formed the pattern → `longterm`.
- Standalone insights discovered during review → `longterm`.
