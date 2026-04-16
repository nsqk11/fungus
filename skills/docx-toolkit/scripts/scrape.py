#!/usr/bin/env python3.12
"""Scrape .docx body into flat JSON keyed by body element index."""

import argparse
import json
import os
from typing import Any

from docx import Document
from lxml import etree
from docx.oxml.ns import qn

# ── XML namespaces ──────────────────────────────────────────────

_MC_NS = (
    "http://schemas.openxmlformats.org/markup-compatibility/2006"
)
_WP_NS = (
    "http://schemas.openxmlformats.org/drawingml/2006/"
    "wordprocessingDrawing"
)
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


# ── Run-level extraction ───────────────────────────────────────


def _run_text(run_el: etree._Element) -> str:
    """Return plain text from a w:r element."""
    parts: list[str] = []
    for child in run_el:
        if child.tag == qn("w:t") and child.text:
            parts.append(child.text)
        elif child.tag == qn("w:br"):
            parts.append("\n")
        elif child.tag == qn("w:tab"):
            parts.append("\t")
    return "".join(parts)


def _extract_image(
    run_el: etree._Element,
    part: Any,
) -> dict[str, Any] | None:
    """Return image info if run contains w:drawing or w:pict."""
    drawing = run_el.find(qn("w:drawing"))
    if drawing is not None:
        img: dict[str, Any] = {"image": True}
        inline = drawing.find(
            f"{{{_WP_NS}}}inline"
        ) or drawing.find(f"{{{_WP_NS}}}anchor")
        if inline is not None:
            for attr, key in (("cx", "width_emu"), ("cy", "height_emu")):
                val = inline.get(attr)
                if val:
                    img[key] = int(val)
            doc_pr = inline.find(f"{{{_WP_NS}}}docPr")
            if doc_pr is not None:
                alt = doc_pr.get("descr")
                if alt:
                    img["alt"] = alt
            blip = inline.find(f".//{{{_A_NS}}}blip")
            if blip is not None:
                r_embed = blip.get(qn("r:embed"))
                if r_embed and r_embed in part.rels:
                    img["rId"] = r_embed
                    img["target"] = part.rels[r_embed].target_ref
        return img
    if run_el.find(qn("w:pict")) is not None:
        return {"image": True}
    return None


def _extract_run(
    run_el: etree._Element,
    part: Any,
) -> dict[str, Any] | None:
    """Return text run dict, image dict, or None."""
    img = _extract_image(run_el, part)
    if img:
        return img
    text = _run_text(run_el)
    if not text:
        return None
    run: dict[str, Any] = {"text": text}
    rpr = run_el.find(qn("w:rPr"))
    if rpr is not None:
        for tag, key in (
            ("w:b", "bold"),
            ("w:i", "italic"),
            ("w:vanish", "hidden"),
        ):
            if rpr.find(qn(tag)) is not None:
                run[key] = True
    return run


# ── Paragraph-level extraction ─────────────────────────────────


def _extract_runs(
    para_el: etree._Element,
    part: Any,
) -> list[dict[str, Any]]:
    """Extract runs from a w:p, handling hyperlinks and fields."""
    runs: list[dict[str, Any]] = []
    in_field = False
    for child in para_el:
        if child.tag == qn("w:r"):
            for fc in child.findall(qn("w:fldChar")):
                ftype = fc.get(qn("w:fldCharType"))
                if ftype == "begin":
                    in_field = True
                elif ftype in ("separate", "end"):
                    in_field = False
            if in_field:
                continue
            run = _extract_run(child, part)
            if run:
                runs.append(run)
        elif child.tag == qn("w:hyperlink"):
            if in_field:
                continue
            _extract_hyperlink(child, part, runs)
        elif child.tag == qn("w:sdt"):
            _extract_sdt_runs(child, part, runs)
    return runs


def _extract_hyperlink(
    hl_el: etree._Element,
    part: Any,
    runs: list[dict[str, Any]],
) -> None:
    """Append hyperlink run to runs list."""
    r_id = hl_el.get(qn("r:id"))
    url = ""
    if r_id and r_id in part.rels:
        url = part.rels[r_id].target_ref
    texts = [_run_text(r) for r in hl_el.findall(qn("w:r"))]
    joined = "".join(t for t in texts if t)
    if joined:
        entry: dict[str, Any] = {"text": joined}
        if url:
            entry["hyperlink"] = url
        runs.append(entry)


def _extract_sdt_runs(
    sdt_el: etree._Element,
    part: Any,
    runs: list[dict[str, Any]],
) -> None:
    """Append runs from a structured document tag."""
    content = sdt_el.find(qn("w:sdtContent"))
    if content is None:
        return
    for r in content.findall(qn("w:r")):
        run = _extract_run(r, part)
        if run:
            runs.append(run)


# ── Table extraction ───────────────────────────────────────────


def _extract_table(
    tbl_el: etree._Element,
    part: Any,
) -> list[dict[str, Any]]:
    """Extract all cells from a w:tbl element."""
    cells: list[dict[str, Any]] = []
    for row_idx, tr in enumerate(tbl_el.findall(qn("w:tr"))):
        for col_idx, tc in enumerate(tr.findall(qn("w:tc"))):
            cell = _extract_cell(tc, row_idx, col_idx, part)
            cells.append(cell)
    return cells


def _extract_cell(
    tc_el: etree._Element,
    row: int,
    col: int,
    part: Any,
) -> dict[str, Any]:
    """Extract a single table cell."""
    cell_runs: list[dict[str, Any]] = []
    for i, para in enumerate(tc_el.findall(qn("w:p"))):
        if i > 0 and cell_runs:
            cell_runs.append({"text": "\n"})
        cell_runs.extend(_extract_runs(para, part))
    text = "".join(r.get("text", "") for r in cell_runs)
    cell: dict[str, Any] = {
        "row": row,
        "col": col,
        "text": text,
        "runs": cell_runs,
    }
    shd = tc_el.find(f'.//{qn("w:shd")}')
    if shd is not None:
        fill = shd.get(qn("w:fill"))
        if fill and fill.upper() not in ("AUTO", "FFFFFF"):
            cell["shading"] = fill
    return cell


# ── Property helpers ───────────────────────────────────────────


def _heading_level(para_el: etree._Element) -> int:
    """Return heading level (1-9) or 0."""
    style = _style_name(para_el)
    if style and style.startswith("Heading"):
        try:
            return int(style.replace("Heading", ""))
        except ValueError:
            pass
    return 0


def _style_name(el: etree._Element) -> str | None:
    """Return paragraph or table style name, or None."""
    # Paragraph style.
    ppr = el.find(qn("w:pPr"))
    if ppr is not None:
        ps = ppr.find(qn("w:pStyle"))
        if ps is not None:
            return ps.get(qn("w:val"))
    # Table style.
    tpr = el.find(qn("w:tblPr"))
    if tpr is not None:
        ts = tpr.find(qn("w:tblStyle"))
        if ts is not None:
            return ts.get(qn("w:val"))
    return None


def _is_list(para_el: etree._Element) -> bool:
    """Return True if paragraph has numbering properties."""
    ppr = para_el.find(qn("w:pPr"))
    return ppr is not None and ppr.find(qn("w:numPr")) is not None


# ── Comments ───────────────────────────────────────────────────


def _parse_comments(doc: Document) -> dict[str, dict[str, str]]:
    """Parse comments.xml into {id: {author, date, text}}."""
    comments: dict[str, dict[str, str]] = {}
    for rel in doc.part.rels.values():
        if "comments" not in rel.reltype:
            continue
        try:
            cxml = rel.target_part.element
        except AttributeError:
            cxml = etree.fromstring(rel.target_part.blob)
        for comment in cxml.findall(qn("w:comment")):
            cid = comment.get(qn("w:id"))
            if cid is None:
                continue
            texts: list[str] = []
            for para in comment.findall(qn("w:p")):
                for run in para.findall(qn("w:r")):
                    for t_el in run.findall(qn("w:t")):
                        if t_el.text:
                            texts.append(t_el.text)
            comments[cid] = {
                "author": comment.get(qn("w:author"), ""),
                "date": comment.get(qn("w:date"), ""),
                "text": "".join(texts),
            }
        break
    return comments


def _map_comments_to_body(
    children: list[etree._Element],
) -> dict[str, int]:
    """Map comment IDs to body indices via commentRangeStart."""
    mapping: dict[str, int] = {}
    for idx, el in enumerate(children):
        for crs in el.iter(qn("w:commentRangeStart")):
            cid = crs.get(qn("w:id"))
            if cid is not None:
                mapping[cid] = idx
    return mapping


# ── Paragraph processing ──────────────────────────────────────


def _build_heading_node(
    idx: int,
    el: etree._Element,
    part: Any,
    style: str | None,
    level: int,
    runs: list[dict[str, Any]],
    heading_stack: list[tuple[str, int]],
    sections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build node dict for a heading paragraph."""
    text = "".join(r.get("text", "") for r in runs).strip()
    while heading_stack and heading_stack[-1][1] >= level:
        heading_stack.pop()
    if heading_stack:
        section_path = f"{heading_stack[-1][0]} > {text}"
    else:
        section_path = text
    heading_stack.append((section_path, level))
    sections[section_path] = {
        "idx": idx,
        "level": level,
        "children": [],
    }
    if len(heading_stack) >= 2:
        parent = heading_stack[-2][0]
        if parent in sections:
            sections[parent]["children"].append(section_path)
    return {
        "tag": "p",
        "style": style or f"Heading{level}",
        "text": text,
        "runs": runs,
        "section": section_path,
        "level": level,
    }


def _build_paragraph_node(
    el: etree._Element,
    part: Any,
    style: str | None,
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build node dict for a non-heading paragraph."""
    text = "".join(r.get("text", "") for r in runs)
    node: dict[str, Any] = {"tag": "p", "text": text, "runs": runs}
    if style and style != "Normal":
        node["style"] = style
    if _is_list(el):
        node["list"] = True
    return node


# ── Main extraction ────────────────────────────────────────────


def extract(docx_path: str) -> dict[str, Any]:
    """Extract docx body into a flat JSON-serializable dict.

    Args:
        docx_path: Path to the .docx file.

    Returns:
        Dict with meta, nodes, and sections keys.
    """
    doc = Document(docx_path)
    part = doc.part
    children = list(doc.element.body)

    nodes: dict[str, dict[str, Any]] = {}
    sections: dict[str, dict[str, Any]] = {}
    heading_stack: list[tuple[str, int]] = []

    for idx, el in enumerate(children):
        tag = el.tag
        if tag == qn("w:p"):
            node = _process_paragraph(
                idx, el, part, heading_stack, sections,
            )
        elif tag == qn("w:tbl"):
            node = _process_table(el, part)
        elif tag == qn("w:sdt"):
            node = {"tag": "sdt", "text": "[StructuredDocumentTag]"}
        else:
            continue
        if node is not None:
            nodes[str(idx)] = node

    _attach_comments(doc, children, nodes)

    return {
        "meta": {
            "source": os.path.basename(docx_path),
            "body_count": len(children),
        },
        "nodes": nodes,
        "sections": sections,
    }


def _process_paragraph(
    idx: int,
    el: etree._Element,
    part: Any,
    heading_stack: list[tuple[str, int]],
    sections: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Process a w:p element into a node dict."""
    # AlternateContent — preserve raw XML.
    if el.find(f".//{{{_MC_NS}}}AlternateContent") is not None:
        return {
            "tag": "p",
            "style": _style_name(el),
            "text": "[AlternateContent]",
            "raw_xml": etree.tostring(el, encoding="unicode"),
        }

    style = _style_name(el)
    runs = _extract_runs(el, part)
    level = _heading_level(el)

    if level > 0:
        return _build_heading_node(
            idx, el, part, style, level, runs,
            heading_stack, sections,
        )
    return _build_paragraph_node(el, part, style, runs)


def _process_table(
    el: etree._Element,
    part: Any,
) -> dict[str, Any]:
    """Process a w:tbl element into a node dict."""
    node: dict[str, Any] = {
        "tag": "tbl",
        "cells": _extract_table(el, part),
    }
    style = _style_name(el)
    if style:
        node["style"] = style
    return node


def _attach_comments(
    doc: Document,
    children: list[etree._Element],
    nodes: dict[str, dict[str, Any]],
) -> None:
    """Attach parsed comments to their body nodes."""
    comments_data = _parse_comments(doc)
    if not comments_data:
        return
    comment_map = _map_comments_to_body(children)
    for cid, body_idx in comment_map.items():
        if cid in comments_data and str(body_idx) in nodes:
            target = nodes[str(body_idx)]
            if "comments" not in target:
                target["comments"] = []
            entry = {"id": int(cid)}
            entry.update(comments_data[cid])
            target["comments"].append(entry)


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
            f"Extracted {len(result['nodes'])} nodes, "
            f"{len(result['sections'])} sections → {args.output}"
        )
    else:
        print(out)


if __name__ == "__main__":
    main()
