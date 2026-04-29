# pptx scrape output schema

`scrape.py` on a `.pptx` returns a JSON object keyed by slide index (slide
1 uses key `"1"`, following the presentation's rId order rather than the
numeric file suffix under `ppt/slides/`).

## Shape types

Every shape under a slide has a `type`:

| Shape type | Description |
|------------|-------------|
| `text` | Text box or auto shape with text |
| `table` | Table shape |
| `image` | Picture (position only — pixels not extracted) |
| `chart` | Embedded chart |
| `group` | Grouped shapes; recurses via a `children` array |
| `other` | SmartArt, media, or unknown |

## Text / run fields

Runs inside a `text` shape carry:

| Field | Description |
|-------|-------------|
| `text` | Visible text |
| `bold` | Bold |
| `italic` | Italic |
| `size` | Font size in hundredths of a point |
| `color` | Hex colour string if set |
| `hyperlink` | Hyperlink target if present |

## Table cell fields

Cells inside a `table` shape carry:

| Field | Description |
|-------|-------------|
| `row` | 0-based row index |
| `col` | 0-based column index |
| `text` | Concatenated cell text |
| `runs` | Run list (same shape as text runs above) |
| `shading` | Cell background (hex if set) |

## Notes

- Grouped shapes are flattened by recursing into `p:grpSp`; text inside
  groups is preserved but nested under `children`.
- Placeholder shapes carry the `p:ph` type attribute; check it to
  distinguish titles, bodies, and other reserved slots.
- SmartArt text lives in a separate XML part; the scraper marks it as
  `other` and text may be incomplete.
