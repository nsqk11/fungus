# Gotchas

Known pitfalls when scraping or patching Office documents. Keep this
list short — each entry should come from a real bug someone hit.

## pptx

| Pitfall | Correct approach |
|---------|-----------------|
| Slide order ≠ file numbering | Read `presentation.xml` rId order; don't sort by `slide1.xml` / `slide2.xml` numerically |
| Grouped shapes hide text | Recurse into `p:grpSp` children |
| SmartArt text lives in a separate XML part | Scraper marks as `other`; text may be incomplete |
| Placeholder titles are special | Check `p:ph` type attribute to distinguish titles from body |

## docx

| Pitfall | Correct approach |
|---------|-----------------|
| `update_runs` drops formatting | Include `bold`/`italic` flags in each run dict |
| Multiple `add_after` on the same idx | Use different target indices or chain the ops |
| `.doc` files (legacy binary) | Convert to `.docx` first with LibreOffice |

## Patch order

Mixing modification, structural, and comment ops in the same batch is
fine — the patcher always runs them in three ordered phases
(modification → structural descending-idx → comments). Writing ops in
any order is safe; trying to pre-sort them is not.
