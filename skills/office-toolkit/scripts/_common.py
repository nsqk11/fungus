#!/usr/bin/env python3.12
"""Parse shared helpers for Office XML."""

import zipfile

from lxml import etree

_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def parse_rels(zf: zipfile.ZipFile, rels_path: str) -> dict[str, str]:
    """Parse a .rels file into {rId: target}."""
    if rels_path not in zf.namelist():
        return {}
    tree = etree.fromstring(zf.read(rels_path))
    return {
        rel.get("Id"): rel.get("Target")
        for rel in tree.findall(f"{{{_REL_NS}}}Relationship")
    }
