# Workbench schema

One JSON document per project. The top-level keys are fixed; the
array sections hold records with a small, stable shape.

## Top-level shape

```json
{
  "id": "my-project-2026-q2",
  "name": "Human-readable project name",
  "type": "",
  "status": "active",
  "createdAt": "2026-04-29T08:00:00Z",
  "updatedAt": "2026-04-29T08:00:00Z",
  "deliverables": [],
  "references": [],
  "milestones": [],
  "changeLog": [],
  "reviews": [],
  "notes": []
}
```

### `id`
Stable identifier. Must match `^[A-Za-z0-9._-]+$`, length 1-64. Used
as the filename and as the prefix-match target in every CLI command
except `init` (which requires the full id).

### `name`
Free text. The human-readable label shown by `list` and `status`.

### `type`
Free text, optional. Categorises the project ("feature", "study",
"research", "paper", "ticket"). No enforced values.

### `status`
One of `active`, `paused`, `done`, `archived`.
- `active`: currently in progress. `remind` includes it.
- `paused`: on hold, not being worked on. `remind` skips it.
- `done`: finished. Kept for reference.
- `archived`: finished and hidden from default listings. Use when
  you want `list` (without `--status`) to stay short.

### `createdAt` / `updatedAt`
UTC ISO-8601 with seconds precision (`YYYY-MM-DDTHH:MM:SSZ`). Set
automatically on every write. Do not edit by hand; doing so is
harmless but the next write overwrites `updatedAt`.

## `deliverables` and `references`

Two arrays with the same record shape. Split by direction:

- **deliverables** — things you are producing or editing (output).
- **references** — things you are consuming (input, read-only).

```json
{ "label": "Design doc", "type": "file", "path": "~/work/proj/design.md" }
{ "label": "Spec",       "type": "url",  "url":  "https://..." }
```

`type` is free text; common values: `file`, `url`, `page`, `ticket`.
Exactly one of `path` / `url` is expected, but neither is enforced.

## `milestones`

```json
{ "name": "Final Review", "target": "WK20", "done": false, "note": "" }
```

- `name` is free text. Uniqueness is recommended (update and done
  look up by name).
- `target` is free text. A week label (`WK20`), ISO date
  (`2026-06-01`), or empty all work.
- `done` is a bool. Flipping it to `true` is what `milestone done`
  does.
- `note` holds blocker context ("waiting on PROJ-123", "reviewer
  still drafting comments"). There is deliberately no separate
  "blockers" section — a blocked milestone is a milestone with a
  non-empty note.

## `changeLog`

```json
{ "date": "2026-04-29", "summary": "Revised Section 3 based on review", "ref": "abc1234" }
```

- `date` defaults to today if `--date` is omitted.
- `summary` is a one-liner. Look up details in git, not here.
- `ref` is optional: git sha, PR link, review id, whatever helps you
  find the full change.

## `reviews`

```json
{
  "id": 1,
  "location": "Section 3.2, Table 5",
  "comment": "The wording here is ambiguous.",
  "by": "Alex",
  "response": "Updated wording to ... .",
  "done": true
}
```

- `id` is assigned sequentially per workbench (starts at 1).
- `location` is free text; empty when the review was unscoped.
- `comment` is the verbatim feedback.
- `by` is the reviewer's name or identifier.
- `response` is your reply. Set at `add` time if known, or filled in
  by `review done --response`.
- `done` flips to `true` via `review done`.

## `notes`

```json
{ "topic": "Why we chose approach B", "content": "..." }
```

Free-form decision log. Use `topic` as a short subject and
`content` for the reasoning. Notes are never auto-expired;
distillation is a manual task outside this skill's scope.

## Field path syntax (for `query --field`)

Dot-separated path, evaluated left to right:

- Dict keys: `milestones`, `createdAt`.
- List indices (integers): `milestones.0`.
- Nested: `milestones.0.note`, `reviews.2.comment`.

The path must resolve to something present in the document. Paths
that walk off the end print an error.

Limitations by design:

- No filtering (`milestones[?done=false]`-style queries). Use
  `status` or post-process the full JSON.
- No wildcards. The agent writes Python against the JSON for
  anything richer.
