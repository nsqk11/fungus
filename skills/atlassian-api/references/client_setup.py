#!/usr/bin/env python3.12
"""Template: write your own Atlassian API code using atlassian-python-api.

Read this file when you need an operation that the ``atlassian-api`` skill
does not cover (creating or editing pages, JQL/CQL searches, bulk work,
custom fields, attachments, …).

Copy the ``load_pat`` + ``get_confluence`` / ``get_jira`` helpers below
into your own script (or import this module directly) and call any method
on the returned client from atlassian-python-api.

Docs: https://atlassian-python-api.readthedocs.io

Key rules
---------
1. The PAT must stay inside the Python process. Do not print it, do not
   pass it through shell arguments, do not write it to logs.
2. Use ``atlassian-python-api``. Do not write raw ``requests`` calls to
   Atlassian REST endpoints; the library handles auth, pagination, and
   error shape for you.
3. Keep your script narrow. Each task probably has a few API calls; do
   not build a framework.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from atlassian import Confluence, Jira


def _resolve_db() -> Path:
    """Locate the atlassian-api skill's SQLite store."""
    override = os.environ.get("ATLASSIAN_API_DB")
    if override:
        return Path(override)
    # This file sits at <skill>/references/; the DB lives at <skill>/data/store.db.
    return Path(__file__).resolve().parent.parent / "data" / "store.db"


def load_pat(domain: str) -> str:
    """Return the stored PAT for *domain* or raise KeyError.

    The domain must match what was used in ``atlassian-api token set``.
    """
    db = _resolve_db()
    if not db.exists():
        raise KeyError(
            f"No PAT store found at {db}; run 'atlassian-api token set "
            f"{domain} <pat>' first."
        )
    row = sqlite3.connect(db).execute(
        "SELECT pat FROM tokens WHERE domain = ?", (domain,),
    ).fetchone()
    if not row:
        raise KeyError(
            f"No PAT stored for {domain}; run 'atlassian-api token set "
            f"{domain} <pat>' first."
        )
    return row[0]


def get_confluence(domain: str) -> Confluence:
    """Return a ``Confluence`` client authenticated for *domain*."""
    return Confluence(url=f"https://{domain}", token=load_pat(domain))


def get_jira(domain: str) -> Jira:
    """Return a ``Jira`` client authenticated for *domain*."""
    return Jira(url=f"https://{domain}", token=load_pat(domain))


# ---------------------------------------------------------------------------
# Examples — delete before committing your own script.
# ---------------------------------------------------------------------------


def example_create_confluence_page(
    domain: str, space: str, title: str, body_html: str
) -> dict:
    """Create a new page under *space* with Storage-format HTML body."""
    c = get_confluence(domain)
    return c.create_page(
        space=space,
        title=title,
        body=body_html,
        representation="storage",
    )


def example_update_confluence_page(
    domain: str, page_id: str, new_title: str, new_body_html: str
) -> dict:
    """Replace the body of an existing page."""
    c = get_confluence(domain)
    return c.update_page(
        page_id=page_id,
        title=new_title,
        body=new_body_html,
        representation="storage",
    )


def example_jql_search(domain: str, jql: str, limit: int = 50) -> list[dict]:
    """Run a JQL search and return matching issues."""
    j = get_jira(domain)
    result = j.jql(jql, limit=limit)
    return result.get("issues", []) if isinstance(result, dict) else list(result)


def example_add_jira_comment(
    domain: str, issue_key: str, body: str
) -> dict:
    """Add a comment to an issue."""
    j = get_jira(domain)
    return j.issue_add_comment(issue_key, body)


if __name__ == "__main__":  # pragma: no cover
    import sys

    # Tiny self-test: print whether a PAT is loadable for the domain given
    # on the command line. Does not print the PAT itself.
    if len(sys.argv) != 2:
        print("Usage: client_setup.py <domain>", file=sys.stderr)
        raise SystemExit(2)
    try:
        load_pat(sys.argv[1])
    except KeyError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
    print(f"PAT present for {sys.argv[1]}")
