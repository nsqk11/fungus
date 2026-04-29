---
name: office-toolkit
description: "Scrape and patch Office documents (docx, pptx, xlsx) and PDF into JSON via XML. Use when reading or modifying document content. Trigger on mentions of 'docx', 'pptx', 'xlsx', 'pdf', 'scrape', 'patch', 'Office document', or 'slide content'. Do NOT use for Confluence pages or plain text."
---

# office-toolkit

Scrape and patch Office documents and PDF into structured JSON via direct
XML parsing — no `python-docx`, no `python-pptx`, just `zipfile` + `lxml`
for OOXML and `pymupdf` for PDF.

## Boundary

- **Does**
  - Scrape `.docx` body into flat JSON keyed by body element index.
  - Scrape `.pptx` slides into flat JSON keyed by slide index.
  - Scrape `.xlsx` sheets into flat JSON keyed by sheet name.
  - Scrape `.pdf` pages into flat JSON keyed by page index (block-level
    with table detection).
  - Patch `.docx` XML in-place via JSON instructions.
  - Preserve everything not explicitly targeted during a patch.
- **Does not**
  - Edit XML directly — always use patch commands.
  - Extract image pixel content or render diagrams.
  - Handle Confluence pages or plain text files.
  - Use `python-docx` or `python-pptx` — always use zipfile + lxml.

## Entry points

Run scripts from the skill directory. Format is auto-detected by extension.

```
python3.12 scripts/scrape.py <file> [-o output.json]
python3.12 scripts/patch.py  <file> <instructions.json> [-o output]
```

`scrape.py` supports `.docx`, `.pptx`, `.xlsx`, `.pdf`. `patch.py`
currently supports `.docx` only. If `-o` is omitted, `scrape.py` writes
to stdout and `patch.py` overwrites the input.

Use `--help` on either entry point for a quick reminder.

## Layout

```
scripts/
├── _common.py        # Shared .rels parser
├── scrape.py         # Dispatcher by extension
├── patch.py          # Dispatcher by extension
├── docx/{scrape,patch}.py
├── pptx/scrape.py
├── xlsx/scrape.py
└── pdf/scrape.py
```

Each per-format module can also be invoked directly (e.g.
`python3.12 scripts/docx/scrape.py file.docx`) when debugging.

## References (read on demand)

| File | Contents |
|------|----------|
| `references/docx-patch-ops.md` | Full catalogue of patch ops: modification, structural, comment, plus the run-dict format and optional fields |
| `references/docx-fields.md` | docx scrape JSON schema (body nodes, runs, images) |
| `references/pptx-fields.md` | pptx scrape JSON schema (shape types, runs, cells) |
| `references/gotchas.md` | Known pitfalls and their workarounds |

Read the matching reference file before composing a patch instruction
array or interpreting scrape output — they document every field the
scripts emit or expect.

## Patch phases (quick note)

The docx patcher runs ops in three phases automatically:

1. Modification ops (body length unchanged)
2. Structural ops in descending `idx` order (prevents drift)
3. Comment ops

You can mix op types in a single batch; the script sorts them. Do not
pre-sort the list yourself.

## Dependencies

- Python 3.12+
- `lxml` (OOXML parsing)
- `pymupdf` (PDF parsing; only `scripts/pdf/scrape.py` imports it)

The repo-level `install.sh` installs these via the skill's
`requirements.txt`.
