#!/usr/bin/env python3.12
"""Scrape .xlsx sheets into flat JSON via zipfile + lxml."""

import argparse
import json
import os
import zipfile
from typing import Any

from lxml import etree

from _common import parse_rels as _parse_rels

# ── Namespaces ─────────────────────────────────────────────────

_NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _tag(ns: str, local: str) -> str:
    """Build a Clark notation tag from namespace prefix and local name."""
    return f"{{{_NS[ns]}}}{local}"


# ── Precomputed tags ───────────────────────────────────────────

_ROW = _tag("x", "row")
_C = _tag("x", "c")
_V = _tag("x", "v")
_IS = _tag("x", "is")
_T = _tag("x", "t")
_SI = _tag("x", "si")
_SHEET = _tag("x", "sheet")
_SHEET_DATA = _tag("x", "sheetData")


# ── Shared strings ─────────────────────────────────────────────


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """Load shared strings table. Returns empty list if absent."""
    path = "xl/sharedStrings.xml"
    if path not in zf.namelist():
        return []
    tree = etree.fromstring(zf.read(path))
    strings: list[str] = []
    for si in tree.findall(_SI):
        parts: list[str] = []
        for t_el in si.iter(_T):
            if t_el.text:
                parts.append(t_el.text)
        strings.append("".join(parts))
    return strings


# ── Cell extraction ────────────────────────────────────────────


def _cell_value(
    c_el: etree._Element,
    shared: list[str],
) -> str:
    """Extract cell text value."""
    t = c_el.get("t", "")
    if t == "inlineStr":
        is_el = c_el.find(_IS)
        if is_el is not None:
            parts: list[str] = []
            for t_el in is_el.iter(_T):
                if t_el.text:
                    parts.append(t_el.text)
            return "".join(parts)
        return ""
    v_el = c_el.find(_V)
    if v_el is None or v_el.text is None:
        return ""
    if t == "s":
        idx = int(v_el.text)
        return shared[idx] if idx < len(shared) else ""
    return v_el.text


# ── Sheet extraction ───────────────────────────────────────────


def _load_hyperlinks(
    zf: zipfile.ZipFile,
    sheet_path: str,
    sheet_tree: etree._Element,
) -> dict[str, str]:
    """Build {cell_ref: url} from sheet hyperlinks and rels."""
    rels_path = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
    rels = _parse_rels(zf, rels_path)
    links: dict[str, str] = {}
    r_ns = _NS["r"]
    for hl in sheet_tree.findall(f".//{_tag('x', 'hyperlink')}"):
        ref = hl.get("ref", "")
        r_id = hl.get(f"{{{r_ns}}}id", "")
        if ref and r_id and r_id in rels:
            links[ref] = rels[r_id]
    return links


def _extract_sheet(
    zf: zipfile.ZipFile,
    sheet_path: str,
    shared: list[str],
) -> list[dict[str, Any]]:
    """Extract rows from a single worksheet."""
    tree = etree.fromstring(zf.read(sheet_path))
    sheet_data = tree.find(_SHEET_DATA)
    if sheet_data is None:
        return []
    hyperlinks = _load_hyperlinks(zf, sheet_path, tree)
    rows: list[dict[str, Any]] = []
    for row_el in sheet_data.findall(_ROW):
        cells: dict[str, Any] = {}
        for c_el in row_el.findall(_C):
            ref = c_el.get("r", "")
            value = _cell_value(c_el, shared)
            if value:
                if ref in hyperlinks:
                    cells[ref] = {"text": value, "hyperlink": hyperlinks[ref]}
                else:
                    cells[ref] = value
        if cells:
            row_idx = int(row_el.get("r", "0")) - 1
            rows.append({"row": row_idx, "cells": cells})
    return rows


# ── Sheet order ────────────────────────────────────────────────


def _sheet_order(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return ordered list of (sheet_name, sheet_path)."""
    wb = etree.fromstring(zf.read("xl/workbook.xml"))
    rels = _parse_rels(zf, "xl/_rels/workbook.xml.rels")
    sheets: list[tuple[str, str]] = []
    for sheet_el in wb.findall(f".//{_SHEET}"):
        name = sheet_el.get("name", "")
        r_id = sheet_el.get(f"{{{_NS['r']}}}id", "")
        target = rels.get(r_id, "")
        if target:
            path = f"xl/{target}" if not target.startswith("/") else target.lstrip("/")
            sheets.append((name, path))
    return sheets


# ── Main extraction ────────────────────────────────────────────


def extract(xlsx_path: str) -> dict[str, Any]:
    """Extract xlsx sheets into a flat JSON-serializable dict.

    Args:
        xlsx_path: Path to the .xlsx file.

    Returns:
        Dict with meta and sheets keys.
    """
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = _load_shared_strings(zf)
        sheet_list = _sheet_order(zf)
        sheets: dict[str, dict[str, Any]] = {}
        for name, path in sheet_list:
            if path not in zf.namelist():
                continue
            rows = _extract_sheet(zf, path, shared)
            sheets[name] = {"rows": rows}

    return {
        "meta": {
            "source": os.path.basename(xlsx_path),
            "sheet_count": len(sheets),
        },
        "sheets": sheets,
    }


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape .xlsx sheets into flat JSON.",
    )
    parser.add_argument("input", help="Input .xlsx file")
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
            f"Extracted {result['meta']['sheet_count']} sheets"
            f" → {args.output}"
        )
    else:
        print(out)


if __name__ == "__main__":
    main()
