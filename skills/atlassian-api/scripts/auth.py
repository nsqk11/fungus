"""Token storage, testing, and authenticated client factories.

Tokens live in a single SQLite file at ``<skill>/data/store.db`` with file
mode ``0600``. Override the path with the ``ATLASSIAN_API_DB`` environment
variable (useful for tests).

All functions here are safe to call as a library. The ``atlassian`` package
is imported lazily inside the client factories so that pure token CRUD works
without the dependency installed.
"""
from __future__ import annotations

import datetime as _dt
import os
import sqlite3
import stat
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

__all__ = [
    "db_path",
    "normalise_domain",
    "set_token",
    "list_tokens",
    "remove_token",
    "get_token",
    "test_token",
    "get_confluence",
    "get_jira",
    "TokenRecord",
    "TokenStatus",
]

TokenStatus = Literal["ok", "expired", "unknown"]


def db_path() -> Path:
    """Return the SQLite file path, honouring ATLASSIAN_API_DB if set."""
    override = os.environ.get("ATLASSIAN_API_DB")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "store.db"


def normalise_domain(value: str) -> str:
    """Return the bare host for *value*.

    Accepts a bare domain (``example.atlassian.net``) or a full URL
    (``https://example.atlassian.net/wiki/spaces/DEV``). Lowercases the
    result; preserves a custom port if present.
    """
    if not value:
        raise ValueError("domain must be a non-empty string")
    if "://" in value:
        host = urlparse(value).hostname or ""
    else:
        host = value.split("/", 1)[0]
    host = host.strip().lower()
    if not host:
        raise ValueError(f"could not extract a host from {value!r}")
    return host


def _connect() -> sqlite3.Connection:
    """Open the DB, creating schema on first use."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            domain      TEXT PRIMARY KEY,
            pat         TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            last_tested TEXT,
            status      TEXT
        )
        """
    )
    return conn


def _secure_db() -> None:
    path = db_path()
    if path.exists():
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class TokenRecord:
    """Row wrapper returned by ``list_tokens``."""

    __slots__ = ("domain", "created_at", "last_tested", "status")

    def __init__(
        self,
        domain: str,
        created_at: str,
        last_tested: str | None,
        status: str | None,
    ) -> None:
        self.domain = domain
        self.created_at = created_at
        self.last_tested = last_tested
        self.status = status

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TokenRecord(domain={self.domain!r}, "
            f"created_at={self.created_at!r}, "
            f"last_tested={self.last_tested!r}, status={self.status!r})"
        )


# --- CRUD ---


def set_token(domain: str, pat: str) -> None:
    """Insert or update the PAT for *domain*."""
    domain = normalise_domain(domain)
    if not pat:
        raise ValueError("pat must be a non-empty string")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO tokens(domain, pat, created_at, status)
                 VALUES(?, ?, ?, 'unknown')
              ON CONFLICT(domain) DO UPDATE SET
                  pat         = excluded.pat,
                  status      = 'unknown',
                  last_tested = NULL
            """,
            (domain, pat, _now()),
        )
    _secure_db()


def remove_token(domain: str) -> bool:
    """Delete *domain* from the store. Returns True if a row was removed."""
    domain = normalise_domain(domain)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM tokens WHERE domain = ?", (domain,))
        return cur.rowcount > 0


def list_tokens() -> list[TokenRecord]:
    """Return all stored tokens sorted by domain."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT domain, created_at, last_tested, status"
            " FROM tokens ORDER BY domain"
        ).fetchall()
    return [TokenRecord(*row) for row in rows]


def get_token(domain: str) -> str:
    """Return the stored PAT for *domain* or raise ``KeyError``."""
    domain = normalise_domain(domain)
    with _connect() as conn:
        row = conn.execute(
            "SELECT pat FROM tokens WHERE domain = ?", (domain,)
        ).fetchone()
    if not row:
        raise KeyError(f"No token stored for {domain}")
    return row[0]


def _write_status(domain: str, status: TokenStatus) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tokens SET last_tested = ?, status = ? WHERE domain = ?",
            (_now(), status, domain),
        )


def test_token(domain: str) -> TokenStatus:
    """Probe the token and persist the result.

    Returns ``"ok"`` / ``"expired"`` / ``"unknown"``. Raises ``KeyError``
    if no token is stored for *domain*.
    """
    domain = normalise_domain(domain)
    get_token(domain)  # raises KeyError if missing
    try:
        client = get_confluence(domain)
        client.get_all_spaces(limit=1)
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        if "401" in message or "403" in message:
            _write_status(domain, "expired")
            return "expired"
        _write_status(domain, "unknown")
        return "unknown"
    _write_status(domain, "ok")
    return "ok"


# --- Client factories ---


def get_confluence(domain: str):  # type: ignore[no-untyped-def]
    """Return an ``atlassian.Confluence`` client pre-configured with the PAT."""
    from atlassian import Confluence  # lazy — avoid import cost for CRUD-only use

    domain = normalise_domain(domain)
    return Confluence(url=f"https://{domain}", token=get_token(domain))


def get_jira(domain: str):  # type: ignore[no-untyped-def]
    """Return an ``atlassian.Jira`` client pre-configured with the PAT."""
    from atlassian import Jira

    domain = normalise_domain(domain)
    return Jira(url=f"https://{domain}", token=get_token(domain))
