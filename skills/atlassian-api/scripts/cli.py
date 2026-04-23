#!/usr/bin/env python3.12
"""Atlassian token management and Confluence page caching.

Usage:
    cli.py <command> [args...]
    cli.py --help
    cli.py <command> --help

Commands:
    token   Manage Bearer tokens per domain
    page    Fetch and cache a Confluence page
    lookup  Search local page cache by keyword
"""
import os
import sqlite3
import stat
import sys

from atlassian import Confluence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert

_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "store.db"
)

HELP = {
    "token": (
        "Manage Bearer tokens per domain.\n\n"
        "Usage:\n"
        "    cli.py token list\n"
        "    cli.py token set <domain> <pat>\n"
        "    cli.py token remove <domain>\n"
        "    cli.py token test <domain>\n"
        "    cli.py token get <domain>"
    ),
    "page": (
        "Fetch and cache a Confluence page.\n\n"
        "Usage: cli.py page <domain> <pageId>\n\n"
        "Checks remote version against local cache.\n"
        "Only fetches full content when page has changed."
    ),
    "lookup": (
        "Search local page cache by keyword.\n\n"
        "Usage: cli.py lookup <keyword> [<domain>]\n\n"
        "All words must match title (case-insensitive).\n"
        "Optional domain limits search scope."
    ),
}


def _die(msg):
    """Print error to stderr and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _db():
    """Return a SQLite connection with tables ready."""
    os.makedirs(os.path.dirname(_DB), exist_ok=True)
    conn = sqlite3.connect(_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tokens(
            domain TEXT PRIMARY KEY, pat TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cache(
            domain  TEXT NOT NULL, page_id TEXT NOT NULL,
            title   TEXT DEFAULT '', version INTEGER DEFAULT 0,
            author  TEXT DEFAULT '', updated TEXT DEFAULT '',
            content TEXT DEFAULT '',
            PRIMARY KEY (domain, page_id));
    """)
    return conn


def _secure_db():
    """Restrict DB file to owner read/write."""
    if os.path.exists(_DB):
        os.chmod(_DB, stat.S_IRUSR | stat.S_IWUSR)


def _get_token(domain):
    """Look up PAT for *domain*, or exit."""
    with _db() as conn:
        row = conn.execute(
            "SELECT pat FROM tokens WHERE domain = ?", (domain,)
        ).fetchone()
    if not row:
        _die(f"No token for {domain}")
    return row[0]


def _confluence(domain):
    """Create a Confluence object with token from SQLite."""
    return Confluence(url=f"https://{domain}", token=_get_token(domain))


# --- token ---

def cmd_token(args):
    """Manage Bearer tokens per domain."""
    sub = args[0] if args else ""
    if sub == "list":
        with _db() as conn:
            for row in conn.execute("SELECT domain FROM tokens"):
                print(row[0])
    elif sub == "set":
        if len(args) < 3:
            _die("Usage: token set <domain> <pat>")
        with _db() as conn:
            conn.execute(
                "INSERT INTO tokens(domain, pat) VALUES(?, ?)"
                " ON CONFLICT(domain) DO UPDATE SET pat = excluded.pat",
                (args[1], args[2]),
            )
        _secure_db()
        print(f"Token set for {args[1]}")
    elif sub == "remove":
        if len(args) < 2:
            _die("Usage: token remove <domain>")
        with _db() as conn:
            conn.execute("DELETE FROM tokens WHERE domain = ?", (args[1],))
        print(f"Removed token for {args[1]}")
    elif sub == "test":
        if len(args) < 2:
            _die("Usage: token test <domain>")
        try:
            c = _confluence(args[1])
            c.get_all_spaces(limit=1)
            print(f"OK — token for {args[1]} is valid")
        except Exception as e:
            if "401" in str(e):
                print(f"EXPIRED — token for {args[1]} needs renewal")
            else:
                _die(f"FAILED — {e}")
    elif sub == "get":
        if len(args) < 2:
            _die("Usage: token get <domain>")
        print(_get_token(args[1]))
    else:
        _die("Usage: token {list|set|remove|test|get} [args]")


# --- page ---

def cmd_page(domain, page_id):
    """Fetch page with cache-aware incremental update."""
    c = _confluence(domain)
    meta = c.get_page_by_id(page_id, expand="version")
    title = meta.get("title", "")
    ver = meta.get("version", {})
    version = ver.get("number", 0)
    author = ver.get("by", {}).get("displayName", "")
    updated = ver.get("when", "")

    with _db() as conn:
        cached = conn.execute(
            "SELECT updated, content FROM cache"
            " WHERE domain = ? AND page_id = ?",
            (domain, page_id),
        ).fetchone()

    if cached and cached[0] == updated and cached[1]:
        text = cached[1]
    else:
        full = c.get_page_by_id(page_id, expand="body.storage,version")
        body_html = full.get("body", {}).get("storage", {}).get("value", "")
        text = convert.html2text(body_html, domain, page_id)
        with _db() as conn:
            conn.execute(
                "INSERT INTO cache(domain, page_id, title, version,"
                " author, updated, content) VALUES(?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(domain, page_id) DO UPDATE SET"
                " title=excluded.title, version=excluded.version,"
                " author=excluded.author, updated=excluded.updated,"
                " content=excluded.content",
                (domain, page_id, title, version, author, updated, text),
            )

    print(f"title: {title}")
    print(f"version: {version}")
    print(f"author: {author}")
    print(f"updated: {updated}")
    print("=" * 60)
    print(text)


# --- lookup ---

def cmd_lookup(keyword, domain=None):
    """Search local page cache by keyword."""
    words = keyword.lower().split()
    with _db() as conn:
        if domain:
            rows = conn.execute(
                "SELECT page_id, title FROM cache WHERE domain = ?",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT page_id, title FROM cache").fetchall()
    for page_id, title in rows:
        if all(w in title.lower() for w in words):
            print(f"{page_id}  {title}")


# --- CLI ---

def _extract_domain(s):
    """Extract domain from URL or bare domain string."""
    if s.startswith("http://") or s.startswith("https://"):
        return s.split("/")[2]
    return s


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print(__doc__.strip())
        sys.exit(0)

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if "--help" in rest:
        print(HELP.get(cmd, __doc__.strip()))
        sys.exit(0)

    if cmd == "token":
        cmd_token(rest)
    elif cmd == "page":
        if len(rest) < 2:
            print(HELP["page"])
            sys.exit(0)
        cmd_page(_extract_domain(rest[0]), rest[1])
    elif cmd == "lookup":
        if not rest:
            print(HELP["lookup"])
            sys.exit(0)
        domain = _extract_domain(rest[1]) if len(rest) > 1 else None
        cmd_lookup(rest[0], domain)
    else:
        _die(f"Unknown command: {cmd}")
