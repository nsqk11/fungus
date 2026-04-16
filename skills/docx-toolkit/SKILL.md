---
name: docx-toolkit
description: "[tool] Scrape .docx body into JSON and patch XML
  in-place via instructions. Do NOT edit XML directly."
---

# docx-toolkit

> Scrape and surgically patch `.docx` files via JSON.

## Boundary

- **Does**:
  - Extract body content into flat JSON keyed by body index.
  - Apply patch instructions to modify docx XML in-place.
  - Preserve everything not explicitly targeted.
- **Does not**:
  - Edit XML directly — always use `patch.py`.
  - Handle PDF, PPTX, XLSX, or Confluence pages.
  - Modify headers, footers, styles, numbering, or theme.

## Interface

- **Commands**:
  - `scrape.py` — docx to JSON.
  - `patch.py` — JSON instructions to docx.
- **Input**:
  - `scrape.py`: `.docx` file.
  - `patch.py`: `.docx` file + JSON instruction array.
- **Output**:
  - `scrape.py`: JSON with `meta`, `nodes`, `sections`.
  - `patch.py`: modified `.docx` (in-place or to output path).

## Behavior

### Scrape

Extract body content for reading, analysis, or planning edits.

```bash
python3.12 scrape.py input.docx -o doc.json
```

Output structure:

```json
{
  "meta": {"source": "report.docx", "body_count": 142},
  "nodes": {
    "0":  {"tag": "p", "style": "Title", "text": "...",
           "runs": [...]},
    "34": {"tag": "p", "style": "Heading1", "text": "...",
           "section": "Introduction", "level": 1},
    "35": {"tag": "tbl", "style": "TableGrid",
           "cells": [{"row": 0, "col": 0, "text": "...",
                       "runs": [...]}]}
  },
  "sections": {
    "Introduction": {"idx": 34, "level": 1,
                     "children": [...]}
  }
}
```

Node keys are body element indices (strings).
Use these indices in patch instructions.

Node fields:

| Field | Description |
|-------|-------------|
| `tag` | `p`, `tbl`, or `sdt` |
| `text` | Plain text (runs concatenated) |
| `runs` | Text runs with formatting flags |
| `style` | Paragraph or table style name |
| `level` | Heading level (1-9) |
| `section` | Full section path (headings only) |
| `cells` | Table cells with `row`, `col`, `text`, `runs` |
| `list` | `true` if list paragraph |
| `comments` | Inline comments: `id`, `author`, `date`, `text` |

Image runs: `{"image": true, "rId", "target", "alt?",
"width_emu?", "height_emu?"}`.

### Patch

Apply change instructions to a docx file.

```bash
python3.12 patch.py input.docx instructions.json [-o out.docx]
```

Omit `-o` to overwrite the input file.
Re-scrape after patching if further edits are needed.

Instruction format (JSON array):

```json
[
  {"op": "update_text", "idx": 37, "run": 0,
   "text": "New text"},
  {"op": "update_runs", "idx": 37,
   "runs": [{"text": "New", "bold": true}]},
  {"op": "update_cell", "idx": 35, "row": 0, "col": 1,
   "runs": [{"text": "Done"}]},
  {"op": "rename_heading", "idx": 34, "text": "New Heading"},
  {"op": "add_row", "idx": 35, "after_row": 2,
   "cells": [{"runs": [{"text": "A"}]}]},
  {"op": "delete_row", "idx": 35, "row": 3},
  {"op": "delete", "idx": 50},
  {"op": "add_after", "idx": 37,
   "runs": [{"text": "Inserted"}], "clone_style_from": 37},
  {"op": "add_table_after", "idx": 37,
   "rows": [[{"runs": [{"text": "A"}]}]],
   "clone_style_from": 35},
  {"op": "insert_image", "idx": 37,
   "image_path": "fig.png", "width_cm": 15},
  {"op": "move", "idx": 50, "after": 37},
  {"op": "reply_comment", "comment_id": 1,
   "text": "Done.", "author": "AI"}
]
```

Operations:

| Op | Effect | Lossless? |
|----|--------|-----------|
| `update_text` | Change one run's text | Yes |
| `update_runs` | Replace all runs | pPr kept |
| `update_cell` | Change one table cell | Yes |
| `rename_heading` | Change heading text | Yes |
| `add_row` | Add row after specified row | Clones trPr/tcPr |
| `delete_row` | Delete table row | Yes |
| `delete` | Remove body element | Yes |
| `add_after` | Insert paragraph after target | Style cloned |
| `add_table_after` | Insert table after target | tblPr cloned |
| `insert_image` | Insert image after target | New drawing |
| `move` | Relocate element | Yes |
| `reply_comment` | Add reply to comments.xml | New comment |

Execution order (handled automatically):

1. Modifications first — body length unchanged.
2. Structural changes — sorted by idx descending.
3. Comment replies — applied to comments.xml last.

### Gotchas

| Pitfall | Correct approach |
|---------|-----------------|
| `update_runs` with empty text leaves blank line | Use `delete` to remove the paragraph |
| `update_runs` drops run formatting | Include `bold`/`italic` in run dicts |
| Multiple `add_after` on same idx reverse order | Use different target indices |
| `clone_style_from` body text for heading | Set `pStyle` explicitly |
| Read-only file causes save failure | `chmod` before patching |
