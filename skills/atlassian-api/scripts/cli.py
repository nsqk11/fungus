#!/usr/bin/env python3.12
"""Unified Atlassian REST API client.

Usage:
    cli.py <command> [args...]
    cli.py --help
    cli.py <command> --help

Commands:
    page         Fetch and cache a Confluence page
    lookup       Search local page index by keyword
    search       Search Confluence via CQL
    issue        Fetch a Jira issue
    jql          Search Jira via JQL
    add-comment  Add comment to a Jira issue
    get          Raw GET to any Atlassian URL
    upload       Update a Confluence page
    token        Manage Bearer tokens per domain
"""
import json
import os
import sqlite3
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import client
import convert
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request
from urllib.request import urlopen

_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "store.db"
)

HELP = {
    "page": "Fetch and cache a Confluence page.\n\n"
            "Usage: cli.py page <domain-or-url> <pageId>\n\n"
            "Checks remote updated time against local cache.\n"
            "Only fetches full content when page has changed.",
    "lookup": "Search local page index by keyword.\n\n"
              "Usage: cli.py lookup <keyword> [<domain-or-url>]\n\n"
              "All words must match title (case-insensitive).\n"
              "Optional domain limits search scope.",
    "search": "Search Confluence via CQL.\n\n"
              "Usage: cli.py search <domain-or-url> <query> [--space KEY]\n\n"
              "Returns up to 10 results. Updates local page index.",
    "issue": "Fetch a Jira issue.\n\n"
             "Usage: cli.py issue <domain-or-url> <issueKey>\n\n"
             "Returns JSON with summary, status, description, assignee, "
             "priority, labels.",
    "jql": "Search Jira via JQL.\n\n"
           "Usage: cli.py jql <domain-or-url> <query>\n\n"
           "Returns up to 20 results as JSON.",
    "add-comment": "Add comment to a Jira issue.\n\n"
                   "Usage: cli.py add-comment <domain-or-url> <issueKey> "
                   "<body>",
    "get": "Raw GET to any Atlassian URL.\n\n"
           "Usage: cli.py get <url>\n\n"
           "Domain extracted from URL for token lookup.",
    "upload": "Update a Confluence page with Storage format HTML.\n\n"
              "Usage: cli.py upload <domain-or-url> <pageId> <file>\n\n"
              "Reads current version, increments by 1, PUTs new content.",
    "token": "Manage Bearer tokens per domain.\n\n"
             "Usage:\n"
             "    cli.py token list\n"
             "    cli.py token set <domain> <pat>\n"
             "    cli.py token remove <domain>\n"
             "    cli.py token test <domain>",
}


def die(msg):
    """Print error and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def show_help(command=None):
    """Print help and exit."""
    if command and command in HELP:
        print(HELP[command])
    else:
        print(__doc__.strip())
    sys.exit(0)


def extract_domain(s):
    """Extract domain from URL or bare domain string."""
    if s.startswith("http://") or s.startswith("https://"):
        return s.split("/")[2]
    return s


# --- Database ---

def _db():
    """Return a connection with tables ready."""
    os.makedirs(os.path.dirname(_DB), exist_ok=True)
    conn = sqlite3.connect(_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tokens(
            domain TEXT PRIMARY KEY,
            pat    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cache(
            domain  TEXT NOT NULL,
            page_id TEXT NOT NULL,
            title   TEXT DEFAULT '',
            version INTEGER DEFAULT 0,
            author  TEXT DEFAULT '',
            updated TEXT DEFAULT '',
            content TEXT DEFAULT '',
            PRIMARY KEY (domain, page_id)
        );
    """)
    return conn


def _secure_db():
    """Restrict DB file to owner read/write."""
    if os.path.exists(_DB):
        os.chmod(_DB, stat.S_IRUSR | stat.S_IWUSR)


# --- Token commands ---

def cmd_token(args):
    """Manage Bearer tokens per domain."""
    sub = args[0] if args else ""
    if sub == "list":
        with _db() as conn:
            for row in conn.execute("SELECT domain FROM tokens"):
                print(row[0])
    elif sub == "set":
        if len(args) < 3:
            die("Usage: token set <domain> <pat>")
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
            die("Usage: token remove <domain>")
        with _db() as conn:
            conn.execute(
                "DELETE FROM tokens WHERE domain = ?", (args[1],)
            )
        print(f"Removed token for {args[1]}")
    elif sub == "test":
        if len(args) < 2:
            die("Usage: token test <domain>")
        domain = args[1]
        with _db() as conn:
            row = conn.execute(
                "SELECT pat FROM tokens WHERE domain = ?", (domain,)
            ).fetchone()
        if not row:
            die(f"No token for {domain}")
        tok = row[0]
        for endpoint in [
            f"https://{domain}/rest/api/content?limit=1",
            f"https://{domain}/rest/api/2/serverInfo",
        ]:
            req = Request(endpoint,
                          headers={"Authorization": f"Bearer {tok}"})
            try:
                with urlopen(req) as resp:
                    if resp.status == 200:
                        print(f"OK — token for {domain} is valid")
                        return
            except HTTPError as e:
                if e.code == 401:
                    print(f"EXPIRED — token for {domain} needs renewal")
                    return
                continue
        print(f"FAILED — could not verify token for {domain}")
    else:
        die("Usage: token {list|set|remove|test} [args]")


# --- Page commands ---

def cmd_page(domain, page_id):
    """Fetch page with cache-aware update check."""
    meta_url = f"https://{domain}/rest/api/content/{page_id}?expand=version"
    meta = client.request(meta_url, domain)
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
        full_url = (
            f"https://{domain}/rest/api/content/{page_id}"
            f"?expand=body.storage,version"
        )
        full = client.request(full_url, domain)
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


def cmd_lookup(keyword, domain=None):
    """Search local page index by keyword."""
    words = keyword.lower().split()
    with _db() as conn:
        if domain:
            rows = conn.execute(
                "SELECT page_id, title FROM cache WHERE domain = ?",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT page_id, title FROM cache"
            ).fetchall()
    for page_id, title in rows:
        if all(w in title.lower() for w in words):
            print(f"{page_id}  {title}")


def cmd_search(domain, query, space=None):
    """Search Confluence via CQL."""
    cql = f'type=page AND text~"{query}"'
    if space:
        cql = f"space={space} AND {cql}"
    url = (
        f"https://{domain}/rest/api/content/search"
        f"?cql={quote(cql)}&limit=10"
    )
    data = client.request(url, domain)
    with _db() as conn:
        for r in data.get("results", []):
            pid = str(r.get("id", ""))
            title = r.get("title", "")
            conn.execute(
                "INSERT INTO cache(domain, page_id, title)"
                " VALUES(?, ?, ?)"
                " ON CONFLICT(domain, page_id)"
                " DO UPDATE SET title = excluded.title",
                (domain, pid, title),
            )
            print(f"{pid}  {title}")


# --- Jira commands ---

def cmd_issue(domain, key):
    """Fetch a Jira issue."""
    url = (
        f"https://{domain}/rest/api/2/issue/{key}"
        f"?fields=summary,status,description,assignee,priority,labels"
    )
    print(json.dumps(client.request(url, domain), indent=2,
                     ensure_ascii=False))


def cmd_add_comment(domain, key, body):
    """Add comment to a Jira issue."""
    url = f"https://{domain}/rest/api/2/issue/{key}/comment"
    result = client.request(url, domain, method="POST", data={"body": body})
    print(f"Comment added to {key} (id: {result['id']})")


def cmd_jql(domain, query):
    """Search Jira via JQL."""
    url = (
        f"https://{domain}/rest/api/2/search"
        f"?jql={quote(query)}&maxResults=20"
        f"&fields=summary,status,assignee,priority"
    )
    print(json.dumps(client.request(url, domain), indent=2,
                     ensure_ascii=False))


# --- Utility commands ---

def cmd_get(url):
    """Raw GET to any Atlassian URL."""
    domain = extract_domain(url)
    print(client.request(url, domain, raw=True))


def cmd_upload(domain, page_id, file_path):
    """Update a Confluence page with Storage format HTML."""
    url = (
        f"https://{domain}/rest/api/content/{page_id}"
        f"?expand=version,title"
    )
    data = client.request(url, domain)
    ver = data["version"]["number"]
    title = data["title"]
    with open(file_path) as f:
        body = f.read()
    payload = {
        "id": page_id, "type": "page", "title": title,
        "body": {"storage": {"value": body, "representation": "storage"}},
        "version": {"number": ver + 1},
    }
    result = client.request(url, domain, method="PUT", data=payload)
    print(f"OK — {title} updated to version {result['version']['number']}")


# --- CLI ---

def parse_option(args, name):
    """Extract --name value from args, return (value, remaining)."""
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            die(f"{name} requires a value")
        return args[i + 1], args[:i] + args[i + 2:]
    return None, args


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        show_help()

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if "--help" in rest:
        show_help(cmd)

    space_opt, rest = parse_option(rest, "--space")

    if cmd == "page":
        if len(rest) < 2:
            show_help("page")
        cmd_page(extract_domain(rest[0]), rest[1])
    elif cmd == "lookup":
        if not rest:
            show_help("lookup")
        domain = extract_domain(rest[1]) if len(rest) > 1 else None
        cmd_lookup(rest[0], domain)
    elif cmd == "search":
        if len(rest) < 2:
            show_help("search")
        cmd_search(extract_domain(rest[0]), rest[1], space_opt)
    elif cmd == "issue":
        if len(rest) < 2:
            show_help("issue")
        cmd_issue(extract_domain(rest[0]), rest[1])
    elif cmd == "jql":
        if len(rest) < 2:
            show_help("jql")
        cmd_jql(extract_domain(rest[0]), rest[1])
    elif cmd == "add-comment":
        if len(rest) < 3:
            show_help("add-comment")
        cmd_add_comment(extract_domain(rest[0]), rest[1], rest[2])
    elif cmd == "get":
        if not rest:
            show_help("get")
        cmd_get(rest[0])
    elif cmd == "upload":
        if len(rest) < 3:
            show_help("upload")
        cmd_upload(extract_domain(rest[0]), rest[1], rest[2])
    elif cmd == "token":
        cmd_token(rest)
    else:
        die(f"Unknown command: {cmd}")
