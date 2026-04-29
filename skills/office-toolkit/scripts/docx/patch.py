#!/usr/bin/env python3.12
"""Patch .docx XML in-place via zipfile + lxml.

Usage::

    python3.12 patch_docx.py input.docx instructions.json [-o output.docx]

If -o is omitted, input.docx is overwritten.
"""

import argparse
import json
import os
import shutil
import tempfile
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape as _xml_esc

from lxml import etree

# ── Namespaces ─────────────────────────────────────────────────

_NS = {
    "w": (
        "http://schemas.openxmlformats.org/"
        "wordprocessingml/2006/main"
    ),
    "r": (
        "http://schemas.openxmlformats.org/"
        "officeDocument/2006/relationships"
    ),
    "wp": (
        "http://schemas.openxmlformats.org/"
        "drawingml/2006/wordprocessingDrawing"
    ),
    "a": (
        "http://schemas.openxmlformats.org/"
        "drawingml/2006/main"
    ),
    "pic": (
        "http://schemas.openxmlformats.org/"
        "drawingml/2006/picture"
    ),
    "rel": (
        "http://schemas.openxmlformats.org/"
        "package/2006/relationships"
    ),
}

_RELTYPE_HYPERLINK = (
    "http://schemas.openxmlformats.org/officeDocument/"
    "2006/relationships/hyperlink"
)
_RELTYPE_IMAGE = (
    "http://schemas.openxmlformats.org/officeDocument/"
    "2006/relationships/image"
)


def _tag(ns: str, local: str) -> str:
    """Build a Clark notation tag."""
    return f"{{{_NS[ns]}}}{local}"


# ── Precomputed tags ───────────────────────────────────────────

_P = _tag("w", "p")
_R = _tag("w", "r")
_T = _tag("w", "t")
_BR = _tag("w", "br")
_TAB = _tag("w", "tab")
_RPR = _tag("w", "rPr")
_PPR = _tag("w", "pPr")
_TBL = _tag("w", "tbl")
_TR = _tag("w", "tr")
_TC = _tag("w", "tc")
_TCPR = _tag("w", "tcPr")
_TRPR = _tag("w", "trPr")
_TBLPR = _tag("w", "tblPr")
_TBLGRID = _tag("w", "tblGrid")
_GRIDCOL = _tag("w", "gridCol")
_HYPERLINK = _tag("w", "hyperlink")
_SDT = _tag("w", "sdt")
_DRAWING = _tag("w", "drawing")
_COMMENT = _tag("w", "comment")
_REL_TAG = f"{{{_NS['rel']}}}Relationship"

_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_W_VAL = _tag("w", "val")
_W_ID = _tag("w", "id")
_R_ID = _tag("r", "id")

_REMOVABLE = frozenset({_R, _HYPERLINK, _SDT})

Instr = dict[str, Any]

# ── Image XML template ─────────────────────────────────────────
# Namespace URIs filled at import time. Runtime values use {{...}}.

_IMAGE_TPL = (
    "<w:p"
    ' xmlns:w="{w}"'
    ' xmlns:r="{r}"'
    ' xmlns:wp="{wp}"'
    ' xmlns:a="{a}"'
    ' xmlns:pic="{pic}">'
    "<w:r><w:drawing>"
    '<wp:inline distT="0" distB="0" distL="0" distR="0">'
    '<wp:extent cx="{{cx}}" cy="{{cy}}"/>'
    '<wp:docPr id="{{sid}}" name="{{name}}"/>'
    "<a:graphic>"
    '<a:graphicData uri="{pic}">'
    "<pic:pic>"
    "<pic:nvPicPr>"
    '<pic:cNvPr id="{{sid}}" name="{{name}}"/>'
    "<pic:cNvPicPr/>"
    "</pic:nvPicPr>"
    "<pic:blipFill>"
    '<a:blip r:embed="{{rid}}"/>'
    "<a:stretch><a:fillRect/></a:stretch>"
    "</pic:blipFill>"
    "<pic:spPr>"
    "<a:xfrm>"
    '<a:off x="0" y="0"/>'
    '<a:ext cx="{{cx}}" cy="{{cy}}"/>'
    "</a:xfrm>"
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    "</pic:spPr>"
    "</pic:pic>"
    "</a:graphicData></a:graphic>"
    "</wp:inline>"
    "</w:drawing></w:r></w:p>"
).format(**_NS)


# ── DocxContext ─────────────────────────────────────────────────


class DocxContext:
    """Mutable state for a docx patch session.

    Reads all needed XML into memory at init.
    Does not hold the ZipFile open.
    """

    def __init__(self, zf: zipfile.ZipFile, src_path: str) -> None:
        self.src_path = src_path
        self.zip_names: list[str] = zf.namelist()
        self.doc_tree = etree.fromstring(
            zf.read("word/document.xml"),
        )
        self.body: etree._Element = self.doc_tree.find(
            _tag("w", "body"),
        )
        rels_path = "word/_rels/document.xml.rels"
        if rels_path in self.zip_names:
            self.rels_tree = etree.fromstring(zf.read(rels_path))
        else:
            self.rels_tree = etree.fromstring(
                b"<Relationships"
                b' xmlns="http://schemas.openxmlformats.org'
                b'/package/2006/relationships"/>',
            )
        self.comments_tree: etree._Element | None = None
        if "word/comments.xml" in self.zip_names:
            self.comments_tree = etree.fromstring(
                zf.read("word/comments.xml"),
            )
        self.new_media: list[tuple[str, bytes]] = []

    def next_rid(self) -> str:
        """Allocate next rId."""
        used: set[int] = set()
        for r in self.rels_tree.findall(_REL_TAG):
            rid = r.get("Id", "")
            if rid.startswith("rId"):
                used.add(int(rid[3:]))
        return f"rId{max(used, default=0) + 1}"

    def add_rel(
        self,
        rel_type: str,
        target: str,
        *,
        external: bool = False,
    ) -> str:
        """Add a relationship, return rId."""
        rid = self.next_rid()
        attribs = {"Id": rid, "Type": rel_type, "Target": target}
        if external:
            attribs["TargetMode"] = "External"
        etree.SubElement(self.rels_tree, _REL_TAG, attribs)
        return rid

    def add_hyperlink_rel(self, url: str) -> str:
        """Add external hyperlink rel, return rId."""
        return self.add_rel(
            _RELTYPE_HYPERLINK, url, external=True,
        )

    def add_image_rel(self, image_path: str) -> str:
        """Stage image file and add rel. Return rId."""
        ext = os.path.splitext(image_path)[1].lower()
        existing = [
            n for n in self.zip_names
            if n.startswith("word/media/")
        ]
        idx = len(existing) + len(self.new_media) + 1
        media_name = f"media/image{idx}{ext}"
        with open(image_path, "rb") as f:
            self.new_media.append((f"word/{media_name}", f.read()))
        return self.add_rel(_RELTYPE_IMAGE, media_name)

    def next_shape_id(self) -> int:
        """Find next available shape ID."""
        used: set[int] = set()
        for dp in self.body.iter(_tag("wp", "docPr")):
            v = dp.get("id")
            if v:
                used.add(int(v))
        return max(used, default=0) + 1

    def next_comment_id(self) -> int:
        """Find next available comment ID."""
        if self.comments_tree is None:
            return 1
        used: set[int] = set()
        for c in self.comments_tree.findall(_COMMENT):
            v = c.get(_W_ID)
            if v:
                used.add(int(v))
        return max(used, default=0) + 1


# ── Element builder ────────────────────────────────────────────


def _make(
    tag: str, attribs: dict[str, str] | None = None,
) -> etree._Element:
    """Create a detached XML element."""
    el = etree.Element(tag)
    if attribs:
        for k, v in attribs.items():
            el.set(k, v)
    return el


# ── Run builders ───────────────────────────────────────────────


def _split_text(text: str) -> list[tuple[str, str | None]]:
    """Split text into (kind, value) for w:t / w:br / w:tab."""
    parts: list[tuple[str, str | None]] = []
    buf: list[str] = []
    for ch in text:
        if ch == "\n":
            if buf:
                parts.append(("t", "".join(buf)))
                buf = []
            parts.append(("br", None))
        elif ch == "\t":
            if buf:
                parts.append(("t", "".join(buf)))
                buf = []
            parts.append(("tab", None))
        else:
            buf.append(ch)
    if buf:
        parts.append(("t", "".join(buf)))
    return parts


def _build_rpr(rd: dict[str, Any]) -> etree._Element | None:
    """Build w:rPr from formatting flags, or None."""
    flags = [
        _tag("w", wname)
        for key, wname in (
            ("bold", "b"),
            ("italic", "i"),
            ("hidden", "vanish"),
        )
        if rd.get(key)
    ]
    if not flags:
        return None
    rpr = _make(_RPR)
    for ftag in flags:
        rpr.append(_make(ftag))
    return rpr


def _build_run(rd: dict[str, Any]) -> etree._Element:
    """Build a w:r from a run dict."""
    run = _make(_R)
    rpr = _build_rpr(rd)
    if rpr is not None:
        run.append(rpr)
    for kind, val in _split_text(rd.get("text", "")):
        if kind == "t":
            t_el = _make(_T, {_XML_SPACE: "preserve"})
            t_el.text = val
            run.append(t_el)
        elif kind == "br":
            run.append(_make(_BR))
        elif kind == "tab":
            run.append(_make(_TAB))
    return run


def _build_hyperlink(
    ctx: DocxContext, rd: dict[str, Any],
) -> etree._Element:
    """Build a w:hyperlink with external rel."""
    rid = ctx.add_hyperlink_rel(rd["hyperlink"])
    hl = _make(_HYPERLINK, {_R_ID: rid})
    run = _make(_R)
    rpr = _make(_RPR)
    rpr.append(
        _make(_tag("w", "rStyle"), {_W_VAL: "Hyperlink"}),
    )
    run.append(rpr)
    t_el = _make(_T, {_XML_SPACE: "preserve"})
    t_el.text = rd.get("text", "")
    run.append(t_el)
    hl.append(run)
    return hl


# ── Paragraph helpers ──────────────────────────────────────────


def _clear_runs(p_el: etree._Element) -> None:
    """Remove runs, hyperlinks, sdts. Keep pPr."""
    for child in list(p_el):
        if child.tag in _REMOVABLE:
            p_el.remove(child)


def _inject_runs(
    p_el: etree._Element,
    runs: list[dict[str, Any]],
    ctx: DocxContext,
) -> None:
    """Append run elements to paragraph."""
    for rd in runs:
        if rd.get("hyperlink"):
            p_el.append(_build_hyperlink(ctx, rd))
        else:
            p_el.append(_build_run(rd))


# ── Table helper ───────────────────────────────────────────────


def _get_cell(
    tbl: etree._Element, row: int, col: int,
) -> etree._Element:
    """Return w:tc at (row, col)."""
    trs = tbl.findall(_TR)
    if row >= len(trs):
        raise ValueError(
            f"row {row} out of range ({len(trs)} rows)",
        )
    tcs = trs[row].findall(_TC)
    if col >= len(tcs):
        raise ValueError(
            f"col {col} out of range ({len(tcs)} cols)",
        )
    return tcs[col]


# ── Modification ops (body length unchanged) ──────────────────


def _op_update_text(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Change text of a specific run, preserving formatting."""
    el = ctx.body[idx]
    run_idx = instr["run"]
    all_runs: list[etree._Element] = []
    for child in el:
        if child.tag == _R:
            all_runs.append(child)
        elif child.tag == _HYPERLINK:
            all_runs.extend(child.findall(_R))
    if run_idx >= len(all_runs):
        raise ValueError(
            f"run {run_idx} out of range ({len(all_runs)} runs)",
        )
    target = all_runs[run_idx]
    for tag in (_T, _BR, _TAB):
        for child in target.findall(tag):
            target.remove(child)
    t_el = _make(_T, {_XML_SPACE: "preserve"})
    t_el.text = instr["text"]
    target.append(t_el)


def _op_update_runs(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Replace all runs in a paragraph."""
    _clear_runs(ctx.body[idx])
    _inject_runs(ctx.body[idx], instr["runs"], ctx)


def _op_rename_heading(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Change heading text, preserving first run formatting."""
    el = ctx.body[idx]
    runs = el.findall(_R)
    if not runs:
        return
    t_el = runs[0].find(_T)
    if t_el is not None:
        t_el.text = instr["text"]
    for run in runs[1:]:
        el.remove(run)


def _op_update_cell(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Update a table cell's content."""
    tc = _get_cell(ctx.body[idx], instr["row"], instr["col"])
    paras = tc.findall(_P)
    for p in paras[1:]:
        tc.remove(p)
    if paras:
        _clear_runs(paras[0])
        _inject_runs(paras[0], instr["runs"], ctx)
    else:
        new_p = _make(_P)
        _inject_runs(new_p, instr["runs"], ctx)
        tc.append(new_p)


def _op_add_row(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Add a row after a specified row in a table."""
    tbl = ctx.body[idx]
    trs = tbl.findall(_TR)
    after = instr["after_row"]
    if after >= len(trs):
        raise ValueError(
            f"after_row {after} out of range ({len(trs)} rows)",
        )
    ref_tr = trs[after]
    new_tr = _make(_TR)
    src_trpr = ref_tr.find(_TRPR)
    if src_trpr is not None:
        new_tr.append(deepcopy(src_trpr))
    ref_tcs = ref_tr.findall(_TC)
    cells_data = instr.get("cells", [])
    for col_idx, ref_tc in enumerate(ref_tcs):
        tc = _make(_TC)
        src_tcpr = ref_tc.find(_TCPR)
        if src_tcpr is not None:
            tc.append(deepcopy(src_tcpr))
        new_p = _make(_P)
        if col_idx < len(cells_data):
            _inject_runs(
                new_p, cells_data[col_idx].get("runs", []), ctx,
            )
        tc.append(new_p)
        new_tr.append(tc)
    ref_tr.addnext(new_tr)


def _op_delete_row(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Delete a row from a table."""
    tbl = ctx.body[idx]
    trs = tbl.findall(_TR)
    row = instr["row"]
    if row >= len(trs):
        raise ValueError(
            f"row {row} out of range ({len(trs)} rows)",
        )
    tbl.remove(trs[row])


# ── Structural ops (body length changes) ──────────────────────


def _op_delete(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Remove element from body."""
    ctx.body.remove(ctx.body[idx])


def _op_add_after(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Insert a new paragraph after body[idx]."""
    ref = ctx.body[idx]
    clone_from = instr.get("clone_style_from")
    if clone_from is not None:
        new_p = deepcopy(ctx.body[clone_from])
        _clear_runs(new_p)
    else:
        new_p = _make(_P)
    _inject_runs(new_p, instr["runs"], ctx)
    ref.addnext(new_p)


def _op_add_table_after(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Insert a new table after body[idx]."""
    ref = ctx.body[idx]
    new_tbl = _make(_TBL)
    clone_from = instr.get("clone_style_from")
    if clone_from is not None:
        src_tpr = ctx.body[clone_from].find(_TBLPR)
        if src_tpr is not None:
            new_tbl.append(deepcopy(src_tpr))
    rows = instr["rows"]
    num_cols = len(rows[0]) if rows else 0
    if num_cols:
        grid = _make(_TBLGRID)
        for _ in range(num_cols):
            grid.append(_make(_GRIDCOL))
        new_tbl.append(grid)
    for row_data in rows:
        tr = _make(_TR)
        for cell_data in row_data:
            tc = _make(_TC)
            new_p = _make(_P)
            _inject_runs(
                new_p, cell_data.get("runs", []), ctx,
            )
            tc.append(new_p)
            tr.append(tc)
        new_tbl.append(tr)
    ref.addnext(new_tbl)


def _op_move(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Move element to after body[instr['after']].

    Note: if other structural ops change body length in the same
    batch, the ``after`` index may drift. Use with care.
    """
    el = ctx.body[idx]
    target = ctx.body[instr["after"]]
    ctx.body.remove(el)
    target.addnext(el)


def _op_insert_image(
    ctx: DocxContext, idx: int, instr: Instr,
) -> None:
    """Insert an image paragraph after body[idx].

    Requires ``image_path``, ``width_emu``, ``height_emu``.
    """
    rid = ctx.add_image_rel(instr["image_path"])
    sid = ctx.next_shape_id()
    name = _xml_esc(
        os.path.basename(instr["image_path"]),
        {'"': "&quot;"},
    )
    xml_str = _IMAGE_TPL.format(
        cx=instr["width_emu"],
        cy=instr["height_emu"],
        sid=sid,
        name=name,
        rid=rid,
    )
    new_p = etree.fromstring(xml_str.encode())
    ctx.body[idx].addnext(new_p)


# ── Comment ops ────────────────────────────────────────────────


def _apply_reply_comments(
    ctx: DocxContext, instructions: list[Instr],
) -> int:
    """Apply reply_comment instructions. Return count."""
    replies = [
        i for i in instructions if i["op"] == "reply_comment"
    ]
    if not replies:
        return 0
    if ctx.comments_tree is None:
        raise ValueError("No comments.xml in document")
    for instr in replies:
        cid = ctx.next_comment_id()
        comment = _make(_COMMENT, {
            _W_ID: str(cid),
            _tag("w", "author"): instr.get("author", "AI"),
            _tag("w", "date"): datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ",
            ),
        })
        p = _make(_P)
        run = _make(_R)
        t_el = _make(_T, {_XML_SPACE: "preserve"})
        t_el.text = instr["text"]
        run.append(t_el)
        p.append(run)
        comment.append(p)
        ctx.comments_tree.append(comment)
    return len(replies)


# ── Execution engine ───────────────────────────────────────────

_OPS_MODIFY = {
    "update_text": _op_update_text,
    "update_runs": _op_update_runs,
    "rename_heading": _op_rename_heading,
    "update_cell": _op_update_cell,
    "add_row": _op_add_row,
    "delete_row": _op_delete_row,
}

_OPS_STRUCTURAL = {
    "delete": _op_delete,
    "add_after": _op_add_after,
    "add_table_after": _op_add_table_after,
    "move": _op_move,
    "insert_image": _op_insert_image,
}


def _apply(ctx: DocxContext, instructions: list[Instr]) -> int:
    """Apply instructions in safe order. Return count."""
    # Phase 1: modifications (body length unchanged).
    mods = [i for i in instructions if i["op"] in _OPS_MODIFY]
    for instr in mods:
        _OPS_MODIFY[instr["op"]](ctx, instr["idx"], instr)

    # Phase 2: structural (idx descending to prevent drift).
    structs = [
        i for i in instructions if i["op"] in _OPS_STRUCTURAL
    ]
    structs.sort(key=lambda i: i["idx"], reverse=True)
    for instr in structs:
        _OPS_STRUCTURAL[instr["op"]](ctx, instr["idx"], instr)

    # Phase 3: comments (independent of body indices).
    return len(mods) + len(structs) + _apply_reply_comments(
        ctx, instructions,
    )


# ── Save ───────────────────────────────────────────────────────


def _serialize(tree: etree._Element) -> bytes:
    """Serialize an XML tree with declaration."""
    return etree.tostring(
        tree, xml_declaration=True,
        encoding="UTF-8", standalone=True,
    )


def _save(ctx: DocxContext, out_path: str) -> None:
    """Write modified docx. Unchanged files copied byte-for-byte."""
    modified = {"word/document.xml", "word/_rels/document.xml.rels"}
    if ctx.comments_tree is not None:
        modified.add("word/comments.xml")

    fd, tmp = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    try:
        with (
            zipfile.ZipFile(ctx.src_path) as zf_in,
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout,
        ):
            for item in zf_in.infolist():
                if item.filename not in modified:
                    zout.writestr(item, zf_in.read(item.filename))
            zout.writestr(
                "word/document.xml", _serialize(ctx.doc_tree),
            )
            zout.writestr(
                "word/_rels/document.xml.rels",
                _serialize(ctx.rels_tree),
            )
            if ctx.comments_tree is not None:
                zout.writestr(
                    "word/comments.xml",
                    _serialize(ctx.comments_tree),
                )
            for media_path, data in ctx.new_media:
                zout.writestr(media_path, data)
        shutil.move(tmp, out_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ── Public entry point ─────────────────────────────────────────


def patch(
    docx_path: str,
    instructions: list[Instr],
    out_path: str | None = None,
) -> int:
    """Patch a docx file. Return number of instructions applied."""
    out = out_path or docx_path
    with zipfile.ZipFile(docx_path) as zf:
        ctx = DocxContext(zf, docx_path)
    # zf closed — safe to overwrite src.
    count = _apply(ctx, instructions)
    _save(ctx, out)
    return count


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Patch .docx XML in-place via instructions.",
    )
    parser.add_argument("docx", help="Input .docx file")
    parser.add_argument(
        "instructions", help="Instructions JSON file",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output .docx (default: overwrite input)",
    )
    args = parser.parse_args()

    with open(args.instructions, encoding="utf-8") as f:
        instructions = json.load(f)

    count = patch(args.docx, instructions, args.output)
    out = args.output or args.docx
    print(f"Applied {count} instructions → {out}")


if __name__ == "__main__":
    main()
