#!/usr/bin/env python3.12
"""Scrape .pptx slides into flat JSON via zipfile + lxml."""

import argparse
import json
import os
import zipfile
from typing import Any

from lxml import etree

# ── Namespaces ─────────────────────────────────────────────────

_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _tag(ns: str, local: str) -> str:
    """Build a Clark notation tag from namespace prefix and local name."""
    return f"{{{_NS[ns]}}}{local}"


# ── Precomputed tags ───────────────────────────────────────────

_SP = _tag("p", "sp")
_PIC = _tag("p", "pic")
_GF = _tag("p", "graphicFrame")
_GRPSP = _tag("p", "grpSp")
_TITLE_TYPES = {"title", "ctrTitle"}


# ── Relationship helpers ───────────────────────────────────────


from _common import parse_rels as _parse_rels


def _slide_order(zf: zipfile.ZipFile) -> list[str]:
    """Return ordered list of slide XML paths from presentation.xml."""
    pres = etree.fromstring(zf.read("ppt/presentation.xml"))
    rels = _parse_rels(zf, "ppt/_rels/presentation.xml.rels")
    paths: list[str] = []
    for sld_id in pres.findall(f".//{_tag('p', 'sldId')}"):
        r_id = sld_id.get(f"{{{_NS['r']}}}id")
        target = rels.get(r_id, "") if r_id else ""
        if target.startswith("slides/"):
            paths.append(f"ppt/{target}")
    return paths


# ── Common helpers ─────────────────────────────────────────────


def _get_cNvPr_name(parent: etree._Element) -> str:
    """Get shape name from the first p:cNvPr descendant."""
    cnv = parent.find(f".//{_tag('p', 'cNvPr')}")
    return cnv.get("name", "") if cnv is not None else ""


def _get_srgb_color(parent: etree._Element) -> str | None:
    """Get sRGB hex color from a:solidFill/a:srgbClr under parent."""
    clr = parent.find(f"{_tag('a', 'solidFill')}/{_tag('a', 'srgbClr')}")
    return clr.get("val") if clr is not None else None


def _get_extent(sppr: etree._Element) -> dict[str, int]:
    """Get width/height EMU from a:xfrm/a:ext under spPr."""
    dims: dict[str, int] = {}
    xfrm = sppr.find(_tag("a", "xfrm"))
    if xfrm is None:
        return dims
    ext = xfrm.find(_tag("a", "ext"))
    if ext is None:
        return dims
    cx = ext.get("cx")
    cy = ext.get("cy")
    if cx:
        dims["width_emu"] = int(cx)
    if cy:
        dims["height_emu"] = int(cy)
    return dims


# ── Run extraction ─────────────────────────────────────────────


def _extract_run(r_el: etree._Element) -> dict[str, Any] | None:
    """Extract a single a:r text run."""
    t_el = r_el.find(_tag("a", "t"))
    if t_el is None or not t_el.text:
        return None
    run: dict[str, Any] = {"text": t_el.text}
    rpr = r_el.find(_tag("a", "rPr"))
    if rpr is None:
        return run
    if rpr.get("b") == "1":
        run["bold"] = True
    if rpr.get("i") == "1":
        run["italic"] = True
    sz = rpr.get("sz")
    if sz:
        run["size"] = int(sz)
    color = _get_srgb_color(rpr)
    if color:
        run["color"] = color
    hlr = rpr.find(_tag("a", "hlinkClick"))
    if hlr is not None:
        run["hyperlink"] = hlr.get(f"{{{_NS['r']}}}id", "")
    return run


def _extract_text_body(
    txbody: etree._Element,
) -> tuple[str, list[dict[str, Any]]]:
    """Extract text and runs from a:txBody."""
    runs: list[dict[str, Any]] = []
    for p_el in txbody.findall(_tag("a", "p")):
        if runs:
            runs.append({"text": "\n"})
        for child in p_el:
            if child.tag == _tag("a", "r"):
                run = _extract_run(child)
                if run:
                    runs.append(run)
            elif child.tag == _tag("a", "br"):
                runs.append({"text": "\n"})
    text = "".join(r.get("text", "") for r in runs)
    return text, runs


# ── Table extraction ───────────────────────────────────────────


def _extract_table(tbl_el: etree._Element) -> list[dict[str, Any]]:
    """Extract cells from a:tbl."""
    cells: list[dict[str, Any]] = []
    for row_idx, tr in enumerate(tbl_el.findall(_tag("a", "tr"))):
        for col_idx, tc in enumerate(tr.findall(_tag("a", "tc"))):
            txbody = tc.find(_tag("a", "txBody"))
            if txbody is not None:
                text, runs = _extract_text_body(txbody)
            else:
                text, runs = "", []
            cell: dict[str, Any] = {
                "row": row_idx,
                "col": col_idx,
                "text": text,
                "runs": runs,
            }
            tc_pr = tc.find(_tag("a", "tcPr"))
            if tc_pr is not None:
                shading = _get_srgb_color(tc_pr)
                if shading:
                    cell["shading"] = shading
            cells.append(cell)
    return cells


# ── Shape extraction ───────────────────────────────────────────


def _extract_shape(sp: etree._Element) -> dict[str, Any] | None:
    """Route a shape element to its type-specific extractor."""
    tag = sp.tag
    if tag == _SP:
        return _extract_sp(sp)
    if tag == _PIC:
        return _extract_pic(sp)
    if tag == _GF:
        return _extract_graphic_frame(sp)
    if tag == _GRPSP:
        return _extract_group(sp)
    return None


def _extract_sp(sp: etree._Element) -> dict[str, Any] | None:
    """Extract text shape (p:sp)."""
    name = _get_cNvPr_name(sp)
    txbody = sp.find(_tag("p", "txBody"))
    if txbody is None:
        return None
    text, runs = _extract_text_body(txbody)
    if not text.strip():
        return None
    return {"type": "text", "name": name, "text": text, "runs": runs}


def _extract_pic(pic: etree._Element) -> dict[str, Any]:
    """Extract picture shape (p:pic)."""
    name = _get_cNvPr_name(pic)
    shape: dict[str, Any] = {"type": "image", "name": name}
    sppr = pic.find(_tag("p", "spPr"))
    if sppr is not None:
        shape.update(_get_extent(sppr))
    return shape


def _extract_graphic_frame(gf: etree._Element) -> dict[str, Any] | None:
    """Extract graphic frame (table, chart, or other)."""
    name = _get_cNvPr_name(gf)
    graphic = gf.find(f"{_tag('a', 'graphic')}/{_tag('a', 'graphicData')}")
    if graphic is None:
        return None
    tbl = graphic.find(_tag("a", "tbl"))
    if tbl is not None:
        return {"type": "table", "name": name, "cells": _extract_table(tbl)}
    uri = graphic.get("uri", "")
    if "chart" in uri:
        return {"type": "chart", "name": name}
    return {"type": "other", "name": name, "uri": uri}


def _extract_group(grp: etree._Element) -> dict[str, Any]:
    """Extract group shape (p:grpSp) recursively."""
    name = _get_cNvPr_name(grp)
    children: list[dict[str, Any]] = []
    for child in grp:
        shape = _extract_shape(child)
        if shape:
            children.append(shape)
    return {"type": "group", "name": name, "children": children}


# ── Slide title detection ──────────────────────────────────────


def _find_title(sp_tree: etree._Element) -> str:
    """Find slide title from placeholder type attribute."""
    for sp in sp_tree.findall(_tag("p", "sp")):
        ph = sp.find(f".//{_tag('p', 'ph')}")
        if ph is not None and ph.get("type", "") in _TITLE_TYPES:
            txbody = sp.find(_tag("p", "txBody"))
            if txbody is not None:
                text, _ = _extract_text_body(txbody)
                return text.strip()
    return ""


# ── Notes extraction ───────────────────────────────────────────


def _extract_notes(zf: zipfile.ZipFile, slide_path: str) -> str:
    """Extract speaker notes for a slide."""
    rels_path = slide_path.replace("slides/", "slides/_rels/") + ".rels"
    rels = _parse_rels(zf, rels_path)
    for target in rels.values():
        if "notesSlide" not in target:
            continue
        notes_path = os.path.normpath(
            f"{os.path.dirname(slide_path)}/{target}"
        )
        if notes_path not in zf.namelist():
            continue
        notes_xml = etree.fromstring(zf.read(notes_path))
        sp_tree = notes_xml.find(
            f"{_tag('p', 'cSld')}/{_tag('p', 'spTree')}"
        )
        if sp_tree is None:
            return ""
        for sp in sp_tree.findall(_tag("p", "sp")):
            ph = sp.find(f".//{_tag('p', 'ph')}")
            if ph is not None and ph.get("type") == "body":
                txbody = sp.find(_tag("p", "txBody"))
                if txbody is not None:
                    text, _ = _extract_text_body(txbody)
                    return text.strip()
    return ""


# ── Main extraction ────────────────────────────────────────────


def extract(pptx_path: str) -> dict[str, Any]:
    """Extract pptx slides into a flat JSON-serializable dict.

    Args:
        pptx_path: Path to the .pptx file.

    Returns:
        Dict with meta and slides keys.
    """
    with zipfile.ZipFile(pptx_path) as zf:
        slide_paths = _slide_order(zf)
        slides: dict[str, dict[str, Any]] = {}
        for idx, slide_path in enumerate(slide_paths):
            slide_xml = etree.fromstring(zf.read(slide_path))
            sp_tree = slide_xml.find(
                f"{_tag('p', 'cSld')}/{_tag('p', 'spTree')}"
            )
            if sp_tree is None:
                continue
            shapes: list[dict[str, Any]] = []
            for child in sp_tree:
                shape = _extract_shape(child)
                if shape:
                    shapes.append(shape)
            slide: dict[str, Any] = {
                "title": _find_title(sp_tree),
                "shapes": shapes,
            }
            notes = _extract_notes(zf, slide_path)
            if notes:
                slide["notes"] = notes
            slides[str(idx)] = slide

    return {
        "meta": {
            "source": os.path.basename(pptx_path),
            "slide_count": len(slides),
        },
        "slides": slides,
    }


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape .pptx slides into flat JSON.",
    )
    parser.add_argument("input", help="Input .pptx file")
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
            f"Extracted {result['meta']['slide_count']} slides"
            f" → {args.output}"
        )
    else:
        print(out)


if __name__ == "__main__":
    main()
