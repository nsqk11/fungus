"""Classify Atlassian URLs into Confluence or Jira based on standard path
patterns.

This module intentionally contains **no hardcoded domain names**. It relies
solely on the URL path conventions used by Atlassian Confluence and Jira
(Data Center and Cloud). Any deployed instance is identified by matching
paths like ``/pages/<id>``, ``/display/<space>/<title>``, ``/wiki/…``, or
``/browse/<KEY>-<N>``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, urlparse

__all__ = ["ResourceKind", "Resource", "classify"]

ResourceKind = Literal["confluence_page", "jira_issue", "unknown"]


@dataclass(frozen=True)
class Resource:
    """The outcome of ``classify(url)``.

    Attributes:
        kind: One of ``"confluence_page"``, ``"jira_issue"``, ``"unknown"``.
        host: Hostname from the URL (empty string if absent).
        page_id: Confluence page id, if extracted.
        space: Confluence space key, if extracted.
        title: Confluence page title (spaces restored from ``+``), if extracted.
        issue_key: Jira issue key like ``PROJ-123``, if extracted.
        path: Original URL path (always populated; useful for debugging).
    """

    kind: ResourceKind
    host: str
    path: str
    page_id: str | None = None
    space: str | None = None
    title: str | None = None
    issue_key: str | None = None


# Compiled once at import time
_RE_PAGES_ID = re.compile(r"/pages/(\d+)(?:/|$)")
_RE_SPACES_PAGES = re.compile(r"/spaces/([^/]+)/pages/(\d+)(?:/([^/?#]+))?")
_RE_DISPLAY = re.compile(r"/display/([^/]+)/([^/?#]+)")
_RE_WIKI_SPACES = re.compile(r"/wiki/spaces/([^/]+)/pages/(\d+)(?:/([^/?#]+))?")
_RE_WIKI_DISPLAY = re.compile(r"/wiki/display/([^/]+)/([^/?#]+)")
_RE_JIRA_BROWSE = re.compile(r"^/browse/([A-Z][A-Z0-9_]+-\d+)")


def classify(url: str) -> Resource:
    """Classify *url* as a Confluence page, Jira issue, or unknown.

    Path patterns recognised (domain-agnostic):

    **Confluence**
      - ``/pages/<id>`` and ``/pages/<id>/<slug>``
      - ``/pages/viewpage.action?pageId=<id>``
      - ``/spaces/<SPACE>/pages/<id>[/<slug>]``
      - ``/display/<SPACE>/<Title>``
      - ``/wiki/spaces/<SPACE>/pages/<id>[/<slug>]`` (Cloud)
      - ``/wiki/display/<SPACE>/<Title>`` (Cloud)

    **Jira**
      - ``/browse/<PROJECT>-<NUMBER>``

    The host is returned for downstream use (PAT lookup), but is never used
    to decide the kind.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""

    # --- Confluence ---

    m = _RE_WIKI_SPACES.search(path)
    if m:
        return Resource(
            kind="confluence_page",
            host=host,
            path=path,
            space=m.group(1),
            page_id=m.group(2),
            title=_unslug(m.group(3)),
        )

    m = _RE_SPACES_PAGES.search(path)
    if m:
        return Resource(
            kind="confluence_page",
            host=host,
            path=path,
            space=m.group(1),
            page_id=m.group(2),
            title=_unslug(m.group(3)),
        )

    m = _RE_WIKI_DISPLAY.search(path)
    if m:
        return Resource(
            kind="confluence_page",
            host=host,
            path=path,
            space=m.group(1),
            title=m.group(2).replace("+", " "),
        )

    m = _RE_DISPLAY.search(path)
    if m:
        return Resource(
            kind="confluence_page",
            host=host,
            path=path,
            space=m.group(1),
            title=m.group(2).replace("+", " "),
        )

    if path.endswith("/pages/viewpage.action"):
        params = parse_qs(query)
        page_id = (params.get("pageId") or [None])[0]
        if page_id:
            return Resource(
                kind="confluence_page",
                host=host,
                path=path,
                page_id=page_id,
            )

    m = _RE_PAGES_ID.search(path)
    if m:
        return Resource(
            kind="confluence_page",
            host=host,
            path=path,
            page_id=m.group(1),
        )

    # --- Jira ---

    m = _RE_JIRA_BROWSE.match(path)
    if m:
        return Resource(
            kind="jira_issue",
            host=host,
            path=path,
            issue_key=m.group(1),
        )

    # --- Unknown ---
    return Resource(kind="unknown", host=host, path=path)


def _unslug(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("-", " ").replace("+", " ")
