# docx patch ops

Instructions are a JSON array. Each op is a dict with at least `"op"` and
`"idx"` (the body element index from scrape output).

## Execution order

The patcher runs in three phases to keep body indices valid across a batch:

1. **Modification ops** — body length does not change
2. **Structural ops** — run in descending `idx` order to prevent drift
3. **Comment ops** — applied last, independent of body indices

## Modification ops

| Op | Required fields | Effect |
|----|----------------|--------|
| `update_text` | `idx`, `run`, `text` | Change text of a specific run by index |
| `update_runs` | `idx`, `runs` | Replace all runs in a paragraph |
| `rename_heading` | `idx`, `text` | Change heading text, keep first run formatting |
| `update_cell` | `idx`, `row`, `col`, `runs` | Replace cell content in a table |
| `add_row` | `idx`, `after_row`, `cells` | Insert row after the specified row |
| `delete_row` | `idx`, `row` | Delete a row from a table |

## Structural ops

| Op | Required fields | Effect |
|----|----------------|--------|
| `delete` | `idx` | Remove body element |
| `add_after` | `idx`, `runs` | Insert paragraph after element |
| `add_table_after` | `idx`, `rows` | Insert table after element |
| `move` | `idx`, `after` | Move element to after another |
| `insert_image` | `idx`, `image_path`, `width_emu`, `height_emu` | Insert image paragraph after element |

## Comment ops

| Op | Required fields | Effect |
|----|----------------|--------|
| `reply_comment` | `text` | Append a comment to `comments.xml` |

Optional: `author` (defaults to `"AI"`).

## Run dict format

```json
{"text": "hello", "bold": true, "italic": true, "hidden": true}
```

Hyperlink run:

```json
{"text": "click me", "hyperlink": "https://example.com"}
```

Text supports `\n` (line break) and `\t` (tab).

## Optional fields

- `clone_style_from`: body index to copy style from (`add_after`,
  `add_table_after`).
- `cells`: array of `{"runs": [...]}` for `add_row`.
- `rows`: array of arrays of `{"runs": [...]}` for `add_table_after`.

## Example

```json
[
  {"op": "rename_heading", "idx": 0, "text": "Introduction"},
  {"op": "update_text", "idx": 3, "run": 1, "text": "updated"},
  {"op": "add_after", "idx": 5,
   "runs": [{"text": "New paragraph.", "bold": true}]},
  {"op": "delete", "idx": 12},
  {"op": "reply_comment", "text": "Please review.", "author": "Claude"}
]
```
