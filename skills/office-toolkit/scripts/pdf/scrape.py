#!/usr/bin/env python3.12
"""Scrape .pdf pages into flat JSON via pymupdf with table detection."""

import argparse
import io
import json
import os
import sys
from typing import Any

import pymupdf


# ── Helpers ────────────────────────────────────────────────────


def _round_bbox(bbox: tuple[float, ...]) -> list[float]:
    """Round bbox values to 1 decimal place."""
    return [round(v, 1) for v in bbox]


def _suppress_stdout(func: Any, *args: Any) -> Any:
    """Call func while suppressing stdout (pymupdf prints advice)."""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return func(*args)
    finally:
        sys.stdout = old


# ── Table extraction ───────────────────────────────────────────


def _extract_table_cells(table: pymupdf.table.Table) -> list[dict[str, Any]]:
    """Extract non-empty cells from a pymupdf Table.

    Args:
        table: A pymupdf Table object.

    Returns:
        List of cell dicts with row, col, text keys.
    """
    cells: list[dict[str, Any]] = []
    for r, row in enumerate(table.extract()):
        for c, val in enumerate(row):
            if val is not None:
                cells.append({"row": r, "col": c, "text": val})
    return cells


# ── Block filtering ────────────────────────────────────────────


def _inside_any_table(
    bbox: tuple[float, ...],
    table_rects: list[pymupdf.Rect],
) -> bool:
    """Check if a block bbox overlaps any table region.

    Args:
        bbox: Block bounding box (x0, y0, x1, y1).
        table_rects: List of table Rect objects.

    Returns:
        True if the block overlaps any table.
    """
    block_rect = pymupdf.Rect(bbox)
    return any(block_rect.intersects(tr) for tr in table_rects)


# ── Text block extraction ─────────────────────────────────────


def _text_from_block(block: dict[str, Any]) -> str:
    """Join lines and spans from a pymupdf text block dict.

    Args:
        block: A pymupdf text block dict (type 0).

    Returns:
        Joined text string.
    """
    return "\n".join(
        " ".join(span["text"] for span in line["spans"])
        for line in block.get("lines", [])
    )


# ── Page extraction ────────────────────────────────────────────


def _extract_page(page: pymupdf.Page) -> dict[str, Any]:
    """Extract blocks from a single PDF page.

    Text and image blocks come from get_text("dict"). Tables are
    detected via find_tables(). Blocks overlapping table regions
    are excluded to avoid duplication.

    Args:
        page: A pymupdf Page object.

    Returns:
        Dict with a blocks list, each having idx, type, bbox.
    """
    tables = _suppress_stdout(page.find_tables)
    table_rects = [pymupdf.Rect(t.bbox) for t in tables.tables]

    blocks: list[dict[str, Any]] = []

    for b in page.get_text("dict")["blocks"]:
        if _inside_any_table(b["bbox"], table_rects):
            continue
        bbox = _round_bbox(b["bbox"])
        if b["type"] == 0:
            text = _text_from_block(b)
            if not text.strip():
                continue
            blocks.append({"type": "text", "text": text, "bbox": bbox})
        else:
            blocks.append({
                "type": "image", "bbox": bbox,
                "width": b.get("width", 0), "height": b.get("height", 0),
            })

    for t in tables.tables:
        blocks.append({
            "type": "table", "bbox": _round_bbox(t.bbox),
            "cells": _extract_table_cells(t),
        })

    blocks.sort(key=lambda b: b["bbox"][1])
    for i, b in enumerate(blocks):
        b["idx"] = i

    return {"blocks": blocks}


# ── Main extraction ────────────────────────────────────────────


def extract(pdf_path: str) -> dict[str, Any]:
    """Extract PDF pages into a flat JSON-serializable dict.

    Args:
        pdf_path: Path to the .pdf file.

    Returns:
        Dict with meta and pages keys.
    """
    doc = pymupdf.open(pdf_path)
    pages: dict[str, dict[str, Any]] = {}
    for i, page in enumerate(doc):
        pages[str(i)] = _extract_page(page)
    return {
        "meta": {
            "source": os.path.basename(pdf_path),
            "page_count": len(doc),
        },
        "pages": pages,
    }


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape .pdf pages into flat JSON.",
    )
    parser.add_argument("input", help="Input .pdf file")
    parser.add_argument(
        "-o", "--output", help="Output .json (default: stdout)",
    )
    args = parser.parse_args()

    result = extract(args.input)
    out = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(
            f"Extracted {result['meta']['page_count']} pages"
            f" → {args.output}"
        )
    else:
        print(out)


if __name__ == "__main__":
    main()
