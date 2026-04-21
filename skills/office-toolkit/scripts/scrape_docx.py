#!/usr/bin/env python3.12
"""Scrape .docx body into flat JSON via zipfile + lxml."""

import argparse
import json
import os
import zipfile
from typing import Any

from lxml import etree

from _common import parse_rels as _parse_rels

# ── Namespaces ─────────────────────────────────────────────────

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def _tag(ns: str, local: str) -> str:
    """Build a Clark notation tag from namespace prefix and local name."""
    return f"{{{_NS[ns]}}}{local}"


# ── Precomputed tags ───────────────────────────────────────────

_P = _tag("w", "p")
_TBL = _tag("w", "tbl")
_SDT = _tag("w", "sdt")
_R = _tag("w", "r")
_T = _tag("w", "t")
_BR = _tag("w", "br")
_TAB = _tag("w", "tab")
_RPR = _tag("w", "rPr")
_PPR = _tag("w", "pPr")
_PSTYLE = _tag("w", "pStyle")
_NUMPR = _tag("w", "numPr")
_HYPERLINK = _tag("w", "hyperlink")
_DRAWING = _tag("w", "drawing")
_PICT = _tag("w", "pict")
_FLDCHAR = _tag("w", "fldChar")
_TR = _tag("w", "tr")
_TC = _tag("w", "tc")
_TBLPR = _tag("w", "tblPr")
_TBLSTYLE = _tag("w", "tblStyle")
_SHD = _tag("w", "shd")
_SDT_CONTENT = _tag("w", "sdtContent")
_COMMENT_RANGE_START = _tag("w", "commentRangeStart")
_VAL = _tag("w", "val")


# ── Run-level extraction ───────────────────────────────────────


def _run_text(r_el: etree._Element) -> str:
    """Return plain text from a w:r element."""
    parts: list[str] = []
    for child in r_el:
        if child.tag == _T and child.text:
            parts.append(child.text)
        elif child.tag == _BR:
            parts.append("\n")
        elif child.tag == _TAB:
            parts.append("\t")
    return "".join(parts)


def _extract_image(
    r_el: etree._Element,
    rels: dict[str, str],
) -> dict[str, Any] | None:
    """Return image info if run contains w:drawing or w:pict."""
    drawing = r_el.find(_DRAWING)
    if drawing is not None:
        img: dict[str, Any] = {"image": True}
        inline = drawing.find(f"{{{_NS['wp']}}}inline")
        if inline is None:
            inline = drawing.find(f"{{{_NS['wp']}}}anchor")
        if inline is not None:
            for attr, key in (("cx", "width_emu"), ("cy", "height_emu")):
                val = inline.get(attr)
                if val:
                    img[key] = int(val)
            blip = inline.find(f".//{{{_NS['a']}}}blip")
            if blip is not None:
                r_embed = blip.get(f"{{{_NS['r']}}}embed")
                if r_embed and r_embed in rels:
                    img["rId"] = r_embed
                    img["target"] = rels[r_embed]
        return img
    if r_el.find(_PICT) is not None:
        return {"image": True}
    return None


def _extract_run(
    r_el: etree._Element,
    rels: dict[str, str],
) -> dict[str, Any] | None:
    """Return text run dict, image dict, or None."""
    img = _extract_image(r_el, rels)
    if img:
        return img
    text = _run_text(r_el)
    if not text:
        return None
    run: dict[str, Any] = {"text": text}
    rpr = r_el.find(_RPR)
    if rpr is not None:
        for tag_str, key in (
            (_tag("w", "b"), "bold"),
            (_tag("w", "i"), "italic"),
            (_tag("w", "vanish"), "hidden"),
        ):
            if rpr.find(tag_str) is not None:
                run[key] = True
    return run


# ── Paragraph-level extraction ─────────────────────────────────


def _extract_runs(
    para_el: etree._Element,
    rels: dict[str, str],
) -> list[dict[str, Any]]:
    """Extract runs from a w:p, handling hyperlinks and fields."""
    runs: list[dict[str, Any]] = []
    in_field = False
    for child in para_el:
        if child.tag == _R:
            for fc in child.findall(_FLDCHAR):
                ftype = fc.get(f"{{{_NS['w']}}}fldCharType")
                if ftype == "begin":
                    in_field = True
                elif ftype in ("separate", "end"):
                    in_field = False
            if in_field:
                continue
            run = _extract_run(child, rels)
            if run:
                runs.append(run)
        elif child.tag == _HYPERLINK:
            if in_field:
                continue
            r_id = child.get(f"{{{_NS['r']}}}id", "")
            url = rels.get(r_id, "")
            texts = [_run_text(r) for r in child.findall(_R)]
            joined = "".join(t for t in texts if t)
            if joined:
                entry: dict[str, Any] = {"text": joined}
                if url:
                    entry["hyperlink"] = url
                runs.append(entry)
        elif child.tag == _SDT:
            content = child.find(_SDT_CONTENT)
            if content is not None:
                for r in content.findall(_R):
                    run = _extract_run(r, rels)
                    if run:
                        runs.append(run)
    return runs


# ── Property helpers ───────────────────────────────────────────


def _style_name(el: etree._Element) -> str | None:
    """Return paragraph or table style name, or None."""
    ppr = el.find(_PPR)
    if ppr is not None:
        ps = ppr.find(_PSTYLE)
        if ps is not None:
            return ps.get(_VAL)
    tpr = el.find(_TBLPR)
    if tpr is not None:
        ts = tpr.find(_TBLSTYLE)
        if ts is not None:
            return ts.get(_VAL)
    return None


def _heading_level(style: str | None) -> int:
    """Return heading level (1-9) or 0."""
    if style and style.startswith("Heading"):
        try:
            return int(style.replace("Heading", ""))
        except ValueError:
            pass
    return 0


def _is_list(para_el: etree._Element) -> bool:
    """Return True if paragraph has numbering properties."""
    ppr = para_el.find(_PPR)
    return ppr is not None and ppr.find(_NUMPR) is not None


# ── Table extraction ───────────────────────────────────────────


def _extract_table(
    tbl_el: etree._Element,
    rels: dict[str, str],
) -> list[dict[str, Any]]:
    """Extract all cells from a w:tbl element."""
    cells: list[dict[str, Any]] = []
    for row_idx, tr in enumerate(tbl_el.findall(_TR)):
        for col_idx, tc in enumerate(tr.findall(_TC)):
            cell_runs: list[dict[str, Any]] = []
            for i, para in enumerate(tc.findall(_P)):
                if i > 0 and cell_runs:
                    cell_runs.append({"text": "\n"})
                cell_runs.extend(_extract_runs(para, rels))
            text = "".join(r.get("text", "") for r in cell_runs)
            cell: dict[str, Any] = {
                "row": row_idx,
                "col": col_idx,
                "text": text,
                "runs": cell_runs,
            }
            shd = tc.find(f".//{_SHD}")
            if shd is not None:
                fill = shd.get(f"{{{_NS['w']}}}fill")
                if fill and fill.upper() not in ("AUTO", "FFFFFF"):
                    cell["shading"] = fill
            cells.append(cell)
    return cells


# ── Comments ───────────────────────────────────────────────────


def _parse_comments(zf: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    """Parse word/comments.xml into {id: {author, date, text}}."""
    path = "word/comments.xml"
    if path not in zf.namelist():
        return {}
    cxml = etree.fromstring(zf.read(path))
    comments: dict[str, dict[str, str]] = {}
    for comment in cxml.findall(_tag("w", "comment")):
        cid = comment.get(f"{{{_NS['w']}}}id")
        if cid is None:
            continue
        texts: list[str] = []
        for para in comment.findall(_P):
            for run in para.findall(_R):
                for t_el in run.findall(_T):
                    if t_el.text:
                        texts.append(t_el.text)
        comments[cid] = {
            "author": comment.get(f"{{{_NS['w']}}}author", ""),
            "date": comment.get(f"{{{_NS['w']}}}date", ""),
            "text": "".join(texts),
        }
    return comments


def _map_comments_to_body(
    children: list[etree._Element],
) -> dict[str, int]:
    """Map comment IDs to body indices via commentRangeStart."""
    mapping: dict[str, int] = {}
    for idx, el in enumerate(children):
        for crs in el.iter(_COMMENT_RANGE_START):
            cid = crs.get(f"{{{_NS['w']}}}id")
            if cid is not None:
                mapping[cid] = idx
    return mapping


# ── Node processing ────────────────────────────────────────────


def _process_paragraph(
    el: etree._Element,
    rels: dict[str, str],
) -> dict[str, Any] | None:
    """Process a w:p element into a node dict."""
    style = _style_name(el)
    runs = _extract_runs(el, rels)
    text = "".join(r.get("text", "") for r in runs)
    level = _heading_level(style)

    if level > 0:
        return {
            "tag": "p",
            "style": style or f"Heading{level}",
            "text": text,
            "runs": runs,
            "level": level,
        }

    node: dict[str, Any] = {"tag": "p", "text": text, "runs": runs}
    if style and style != "Normal":
        node["style"] = style
    if _is_list(el):
        node["list"] = True
    return node


def _process_table(
    el: etree._Element,
    rels: dict[str, str],
) -> dict[str, Any]:
    """Process a w:tbl element into a node dict."""
    node: dict[str, Any] = {
        "tag": "tbl",
        "cells": _extract_table(el, rels),
    }
    style = _style_name(el)
    if style:
        node["style"] = style
    return node


# ── Main extraction ────────────────────────────────────────────


def extract(docx_path: str) -> dict[str, Any]:
    """Extract docx body into a flat JSON-serializable dict.

    Args:
        docx_path: Path to the .docx file.

    Returns:
        Dict with meta and nodes keys.
    """
    with zipfile.ZipFile(docx_path) as zf:
        doc_xml = etree.fromstring(zf.read("word/document.xml"))
        rels = _parse_rels(zf, "word/_rels/document.xml.rels")
        body = doc_xml.find(_tag("w", "body"))
        children = list(body)

        nodes: dict[str, dict[str, Any]] = {}
        for idx, el in enumerate(children):
            tag = el.tag
            if tag == _P:
                node = _process_paragraph(el, rels)
            elif tag == _TBL:
                node = _process_table(el, rels)
            elif tag == _SDT:
                node = {"tag": "sdt", "text": "[StructuredDocumentTag]"}
            else:
                continue
            if node is not None:
                nodes[str(idx)] = node

        comments_data = _parse_comments(zf)
        if comments_data:
            comment_map = _map_comments_to_body(children)
            for cid, body_idx in comment_map.items():
                if cid in comments_data and str(body_idx) in nodes:
                    target = nodes[str(body_idx)]
                    if "comments" not in target:
                        target["comments"] = []
                    entry = {"id": int(cid)}
                    entry.update(comments_data[cid])
                    target["comments"].append(entry)

    return {
        "meta": {
            "source": os.path.basename(docx_path),
            "body_count": len(children),
        },
        "nodes": nodes,
    }


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape .docx body into flat JSON.",
    )
    parser.add_argument("input", help="Input .docx file")
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
            f"Extracted {len(result['nodes'])} nodes → {args.output}"
        )
    else:
        print(out)


if __name__ == "__main__":
    main()
