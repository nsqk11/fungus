---
name: office-toolkit
description: "[tool] Scrape and patch Office documents (docx, pptx,
  xlsx) and PDF into JSON via XML. Use when reading or modifying
  document content. Trigger on mentions of 'docx', 'pptx', 'xlsx',
  'pdf', 'scrape', 'patch', 'Office document', or 'slide content'.
  Do NOT use for Confluence pages (use atlassian-api) or plain text."
---

# office-toolkit

> Scrape and patch Office documents and PDF into structured JSON via direct XML parsing.

## Boundary

- **Does**:
  - Scrape docx body into flat JSON keyed by body element index.
  - Scrape pptx slides into flat JSON keyed by slide index.
  - Scrape xlsx sheets into flat JSON keyed by sheet name.
  - Scrape PDF pages into flat JSON keyed by page index (block-level with table detection).
  - Patch docx XML in-place via JSON instructions.
  - Patch pptx XML in-place via JSON instructions (planned).
  - Preserve everything not explicitly targeted during patch.
- **Does not**:
  - Edit XML directly — always use patch commands.
  - Extract image pixel content or render diagrams.
  - Handle Confluence pages or plain text files.
  - Use python-docx or python-pptx — always use zipfile + lxml.

## Interface

- **Commands**:
  - `scrape.py` — document to JSON. Auto-detects format by extension.
  - `patch.py` — JSON instructions to document. Auto-detects format by extension.
- **Input**:
  - `scrape.py`: `.docx`, `.pptx`, `.xlsx`, or `.pdf` file.
  - `patch.py`: document file + JSON instruction array.
- **Output**:
  - `scrape.py`: JSON to stdout or file (`-o`).
  - `patch.py`: modified document (in-place or to output path).

## Behavior

Run `python3.12 scrape.py --help` or `python3.12 patch.py --help` for usage.

### patch.py

Usage: `python3.12 patch.py <file> <instructions.json> [-o output]`

Instructions are a JSON array of op dicts. Each op has `"op"` and `"idx"` (body element index from scrape output).

Execution order: modification ops first (body length unchanged), then structural ops in descending idx order (prevents drift), then comment ops.

#### Modification ops

| Op | Required fields | Effect |
|----|----------------|--------|
| `update_text` | `idx`, `run`, `text` | Change text of a specific run by index |
| `update_runs` | `idx`, `runs` | Replace all runs in a paragraph |
| `rename_heading` | `idx`, `text` | Change heading text, keep first run formatting |
| `update_cell` | `idx`, `row`, `col`, `runs` | Replace cell content in a table |
| `add_row` | `idx`, `after_row`, `cells` | Insert row after specified row |
| `delete_row` | `idx`, `row` | Delete a row from a table |

#### Structural ops

| Op | Required fields | Effect |
|----|----------------|--------|
| `delete` | `idx` | Remove body element |
| `add_after` | `idx`, `runs` | Insert paragraph after element |
| `add_table_after` | `idx`, `rows` | Insert table after element |
| `move` | `idx`, `after` | Move element to after another |
| `insert_image` | `idx`, `image_path`, `width_emu`, `height_emu` | Insert image paragraph after element |

#### Comment ops

| Op | Required fields | Effect |
|----|----------------|--------|
| `reply_comment` | `text` | Append comment to comments.xml |

Optional: `author` (default `"AI"`).

#### Run dict format

```json
{"text": "hello", "bold": true, "italic": true, "hidden": true}
```

Hyperlink run: `{"text": "click", "hyperlink": "https://..."}`.

Text supports `\n` (line break) and `\t` (tab).

#### Optional fields

- `clone_style_from`: body index to copy style from (`add_after`, `add_table_after`).
- `cells`: array of `{"runs": [...]}` for `add_row`.
- `rows`: array of arrays of `{"runs": [...]}` for `add_table_after`.

### docx fields

| Node field | Description |
|------------|-------------|
| `tag` | `p`, `tbl`, or `sdt` |
| `text` | Plain text (runs concatenated) |
| `runs` | Text runs with formatting flags |
| `style` | Paragraph or table style name |
| `level` | Heading level (1-9) |
| `section` | Full section path (headings only) |
| `cells` | Table cells with `row`, `col`, `text`, `runs` |
| `list` | `true` if list paragraph |
| `comments` | Inline comments: `id`, `author`, `date`, `text` |

Image runs: `image`, `rId`, `target`, `alt`, `width_emu`, `height_emu`.

### pptx fields

| Shape type | Description |
|------------|-------------|
| `text` | Text box or auto shape with text |
| `table` | Table shape |
| `image` | Picture (position only) |
| `chart` | Embedded chart |
| `group` | Grouped shapes (recursive `children`) |
| `other` | SmartArt, media, unknown |

Run fields: `text`, `bold`, `italic`, `size`, `color`, `hyperlink`.

Cell fields: `row`, `col`, `text`, `runs`, `shading`.

### Gotchas

| Pitfall | Correct approach |
|---------|-----------------|
| Slide order ≠ file numbering | Read `presentation.xml` rId order |
| Grouped shapes hide text | Recurse into `p:grpSp` |
| SmartArt text in separate XML | Mark as `other`, text may be incomplete |
| pptx placeholder titles | Check `p:ph` type attribute |
| docx `update_runs` drops formatting | Include `bold`/`italic` in run dicts |
| Multiple `add_after` on same idx | Use different target indices |
