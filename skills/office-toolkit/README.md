# office-toolkit

A Fungus skill that scrapes and patches Office documents (`.docx`, `.pptx`,
`.xlsx`) and PDF files by parsing XML directly. No `python-docx`, no
`python-pptx` — just `zipfile` + `lxml` for OOXML formats and `pymupdf`
for PDF.

## Scope

- **Scrape** — flatten a document into JSON, keyed by body element / slide
  / sheet / page index
- **Patch** — apply a JSON array of ops to a `.docx` (text updates, run
  replacements, structural edits, table manipulation, image insertion,
  comments)

## Requirements

- Python 3.12+
- `lxml` (OOXML parsing)
- `pymupdf` (PDF parsing; used only by `scripts/pdf/scrape.py`)

Install with:

```bash
pip install --user -r requirements.txt
```

Or install all skill dependencies at once via the repository-level
`install.sh`, which iterates every skill's `requirements.txt`.

## Quickstart

### Scrape any supported document

```bash
python3.12 scripts/scrape.py input.docx                 # to stdout
python3.12 scripts/scrape.py input.pptx -o slides.json
python3.12 scripts/scrape.py input.xlsx -o sheet.json
python3.12 scripts/scrape.py input.pdf  -o pages.json
```

Extension is auto-detected; `.docx` / `.pptx` / `.xlsx` / `.pdf` are
supported.

### Patch a `.docx`

```bash
python3.12 scripts/patch.py input.docx ops.json                # overwrite
python3.12 scripts/patch.py input.docx ops.json -o output.docx # to new file
```

`ops.json` is an array of op dicts. See `references/docx-patch-ops.md`
for the full op list and per-op schema.

## Layout

```
office-toolkit/
├── SKILL.md              # Agent-facing overview (entry points + boundary)
├── README.md             # This file
├── requirements.txt
├── scripts/
│   ├── _common.py        # Shared .rels parser
│   ├── scrape.py         # Dispatcher by extension
│   ├── patch.py          # Dispatcher by extension
│   ├── docx/
│   │   ├── scrape.py
│   │   └── patch.py
│   ├── pptx/scrape.py
│   ├── xlsx/scrape.py
│   └── pdf/scrape.py
└── references/
    ├── docx-fields.md    # docx scrape JSON schema
    ├── docx-patch-ops.md # Every patch op and its fields
    ├── pptx-fields.md    # pptx scrape JSON schema
    └── gotchas.md        # Known pitfalls and workarounds
```

## Design decisions

- **Raw XML only** — No `python-docx` / `python-pptx`. The wrapper
  libraries hide XML details the patch pipeline needs (run structure,
  revision ids, relationship ids). Parsing with `lxml` is faster and
  more predictable.
- **Flat JSON output** — Scrape returns a flat index → element map
  rather than a nested tree so patch ops can target a specific index
  without walking the document.
- **Deterministic patch order** — Modification ops run first (body
  length unchanged), then structural ops in descending index order
  (prevents drift), then comment ops. This keeps indices valid across
  a multi-op batch.
- **In-place by default** — `patch.py` overwrites the input unless
  `-o` is given; scraping is always non-destructive.

## Scope boundary

- Does not render images, charts, or SmartArt to pixels.
- Does not read `.doc` (legacy binary); convert with LibreOffice first.
- Does not patch `.pptx`/`.xlsx` structure (planned).
- Does not handle Confluence pages or plain text files.

## License

Same as the parent repository (see repository root `LICENSE`).
