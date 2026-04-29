# docx scrape output schema

`scrape.py` on a `.docx` returns:

```json
{
  "meta": {"source": "file.docx", "body_count": 42},
  "body": {
    "0": { ... },
    "1": { ... },
    ...
  }
}
```

Each numeric key under `body` is a body element index.

## Node fields

| Field | Description |
|-------|-------------|
| `tag` | `p`, `tbl`, or `sdt` |
| `text` | Plain text (runs concatenated) |
| `runs` | Text runs with formatting flags |
| `style` | Paragraph or table style name |
| `level` | Heading level (1–9) |
| `section` | Full section path (heading nodes only) |
| `cells` | Table cells with `row`, `col`, `text`, `runs` |
| `list` | `true` if list paragraph |
| `comments` | Inline comments: `id`, `author`, `date`, `text` |

## Image runs

An image run inside `runs` carries:

| Field | Description |
|-------|-------------|
| `image` | `true` marker |
| `rId` | Relationship id from `document.xml.rels` |
| `target` | Media file path inside the archive |
| `alt` | Alt text |
| `width_emu` | Width in EMUs (914400 = 1 inch) |
| `height_emu` | Height in EMUs |

## Run formatting flags

Within a normal run:

| Field | Type | Description |
|-------|------|-------------|
| `text` | str | Visible text |
| `bold` | bool | Bold |
| `italic` | bool | Italic |
| `hidden` | bool | `w:vanish` marker |
| `hyperlink` | str | Hyperlink target (for linked runs) |
