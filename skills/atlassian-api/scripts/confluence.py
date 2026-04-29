"""Confluence page cache, full-text search, and space title sync.

Stores both the raw Storage-format HTML and a plain-text projection. The
plain-text column is mirrored into an FTS5 virtual table alongside titles
for full-text search. Pages are refreshed only when the remote
``version.number`` differs from the cached value (unless ``refresh=True``).
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, Iterable

import auth
import convert

__all__ = [
    "CachedPage",
    "fetch_page",
    "search_pages",
    "sync_space",
    "Page",
]


@dataclass
class Page:
    """Represents a Confluence page returned by this module."""

    domain: str
    page_id: str
    title: str
    space_key: str
    version: int
    author: str
    updated_at: str
    body_html: str
    body_text: str
    fetched_at: str

    def as_text(self) -> str:
        """Return a human-friendly text representation."""
        lines = [
            f"title: {self.title}",
            f"version: {self.version}",
            f"author: {self.author}",
            f"updated: {self.updated_at}",
            f"space: {self.space_key}",
            "=" * 60,
            self.body_text,
        ]
        return "\n".join(lines)

    def as_json(self) -> str:
        """Return a JSON representation (dict-form, pretty-printed)."""
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


# For backwards compatibility / naming consistency with tests
CachedPage = Page


# --- Schema ---

_SCHEMA_PAGES = """
CREATE TABLE IF NOT EXISTS confluence_pages (
    domain      TEXT NOT NULL,
    page_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    space_key   TEXT DEFAULT '',
    version     INTEGER NOT NULL,
    author      TEXT DEFAULT '',
    updated_at  TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    body_html   TEXT DEFAULT '',
    body_text   TEXT DEFAULT '',
    PRIMARY KEY (domain, page_id)
);
"""

_SCHEMA_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS confluence_pages_fts USING fts5(
    domain UNINDEXED,
    page_id UNINDEXED,
    title,
    body_text,
    tokenize = 'porter unicode61'
);
"""


def _connect() -> sqlite3.Connection:
    """Open the DB shared with auth, creating Confluence tables on demand."""
    path = auth.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    # Ensure token table exists too (normally created by auth._connect)
    conn.executescript(_SCHEMA_PAGES + _SCHEMA_FTS)
    return conn


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _row_to_page(row: Iterable[Any]) -> Page:
    (
        domain,
        page_id,
        title,
        space_key,
        version,
        author,
        updated_at,
        fetched_at,
        body_html,
        body_text,
    ) = row
    return Page(
        domain=domain,
        page_id=str(page_id),
        title=title,
        space_key=space_key or "",
        version=int(version),
        author=author or "",
        updated_at=updated_at,
        fetched_at=fetched_at,
        body_html=body_html or "",
        body_text=body_text or "",
    )


def _upsert(conn: sqlite3.Connection, page: Page) -> None:
    conn.execute(
        """
        INSERT INTO confluence_pages(domain, page_id, title, space_key,
            version, author, updated_at, fetched_at, body_html, body_text)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(domain, page_id) DO UPDATE SET
            title      = excluded.title,
            space_key  = excluded.space_key,
            version    = excluded.version,
            author     = excluded.author,
            updated_at = excluded.updated_at,
            fetched_at = excluded.fetched_at,
            body_html  = excluded.body_html,
            body_text  = excluded.body_text
        """,
        (
            page.domain, page.page_id, page.title, page.space_key,
            page.version, page.author, page.updated_at, page.fetched_at,
            page.body_html, page.body_text,
        ),
    )
    # Refresh FTS index
    conn.execute(
        "DELETE FROM confluence_pages_fts WHERE domain = ? AND page_id = ?",
        (page.domain, page.page_id),
    )
    conn.execute(
        "INSERT INTO confluence_pages_fts(domain, page_id, title, body_text)"
        " VALUES(?, ?, ?, ?)",
        (page.domain, page.page_id, page.title, page.body_text),
    )


def _load_cached(
    conn: sqlite3.Connection, domain: str, page_id: str
) -> Page | None:
    row = conn.execute(
        "SELECT domain, page_id, title, space_key, version, author,"
        " updated_at, fetched_at, body_html, body_text"
        " FROM confluence_pages WHERE domain = ? AND page_id = ?",
        (domain, page_id),
    ).fetchone()
    return _row_to_page(row) if row else None


# --- Public API ---


def fetch_page(
    domain: str,
    page_id: str,
    *,
    refresh: bool = False,
    client: Any | None = None,
) -> Page:
    """Fetch a Confluence page, using the cache where possible.

    With ``refresh=False`` (default), the remote ``version.number`` is
    compared against the cached row. A full fetch is issued only when the
    version changed or no cache exists. With ``refresh=True`` the body is
    always re-downloaded and re-indexed.

    *client* is an optional ``atlassian.Confluence`` instance; if omitted,
    one is constructed via :func:`auth.get_confluence`.
    """
    domain = auth.normalise_domain(domain)
    page_id = str(page_id)
    if client is None:
        client = auth.get_confluence(domain)

    with _connect() as conn:
        cached = _load_cached(conn, domain, page_id)

    if not refresh:
        meta = client.get_page_by_id(page_id, expand="version,space")
        remote_version = int(meta.get("version", {}).get("number", 0))
        if cached and cached.version == remote_version and cached.body_html:
            return cached

    full = client.get_page_by_id(page_id, expand="body.storage,version,space")
    page = _build_page(domain, page_id, full)

    with _connect() as conn:
        _upsert(conn, page)

    return page


def _build_page(domain: str, page_id: str, api: dict[str, Any]) -> Page:
    title = api.get("title", "") or ""
    version_block = api.get("version", {}) or {}
    version = int(version_block.get("number", 0))
    author = ((version_block.get("by") or {}).get("displayName")) or ""
    updated_at = version_block.get("when", "") or ""
    space_block = api.get("space", {}) or {}
    space_key = space_block.get("key", "") or ""
    body_html = (
        ((api.get("body") or {}).get("storage") or {}).get("value", "") or ""
    )
    body_text = convert.html_to_text(body_html, domain, page_id)
    return Page(
        domain=domain,
        page_id=str(page_id),
        title=title,
        space_key=space_key,
        version=version,
        author=author,
        updated_at=updated_at,
        fetched_at=_now(),
        body_html=body_html,
        body_text=body_text,
    )


def search_pages(
    query: str,
    *,
    domain: str | None = None,
    title_only: bool = False,
    limit: int = 50,
) -> list[Page]:
    """Full-text search over the cached Confluence pages.

    With ``title_only=True``, the query runs against the ``title`` column
    only (useful for quick title lookup). Otherwise both ``title`` and
    ``body_text`` are searched via FTS5.
    """
    if not query.strip():
        return []
    fts_query = _quote_fts(query)
    params: list[Any] = []
    if title_only:
        match_clause = "f.title MATCH ?"
    else:
        match_clause = "confluence_pages_fts MATCH ?"
    sql = (
        "SELECT p.domain, p.page_id, p.title, p.space_key, p.version,"
        " p.author, p.updated_at, p.fetched_at, p.body_html, p.body_text"
        " FROM confluence_pages_fts f"
        " JOIN confluence_pages p"
        "   ON p.domain = f.domain AND p.page_id = f.page_id"
        f" WHERE {match_clause}"
    )
    params.append(fts_query)
    if domain:
        sql += " AND p.domain = ?"
        params.append(auth.normalise_domain(domain))
    sql += " ORDER BY bm25(confluence_pages_fts) LIMIT ?"
    params.append(int(limit))
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_page(r) for r in rows]


def _quote_fts(query: str) -> str:
    """Quote each bareword so FTS5 treats them as AND-joined literals."""
    tokens = [t for t in query.split() if t]
    return " ".join(f'"{t.replace(chr(34), "")}"' for t in tokens)


def sync_space(
    domain: str,
    space_key: str,
    *,
    client: Any | None = None,
    batch_size: int = 100,
) -> int:
    """Prime the title cache for every page in *space_key*.

    Stores ``title``, ``space_key``, ``version``, ``updated_at`` and empty
    body columns so that :func:`search_pages` with ``title_only=True`` finds
    pages the caller has not individually fetched. Existing cached rows are
    left untouched if their ``body_html`` is non-empty.

    Returns the number of pages upserted.
    """
    domain = auth.normalise_domain(domain)
    if client is None:
        client = auth.get_confluence(domain)

    count = 0
    start = 0
    while True:
        batch = client.get_all_pages_from_space(
            space=space_key,
            start=start,
            limit=batch_size,
            expand="version",
        ) or []
        if not batch:
            break
        with _connect() as conn:
            for api in batch:
                page_id = str(api.get("id", "") or "")
                if not page_id:
                    continue
                existing = _load_cached(conn, domain, page_id)
                if existing and existing.body_html:
                    continue
                stub = _build_page(domain, page_id, {
                    "title": api.get("title", ""),
                    "version": api.get("version", {}),
                    "space": {"key": space_key},
                    "body": {"storage": {"value": existing.body_html if existing else ""}},
                })
                _upsert(conn, stub)
                count += 1
        if len(batch) < batch_size:
            break
        start += batch_size
    return count
