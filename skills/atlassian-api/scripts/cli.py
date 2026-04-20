#!/usr/bin/env python3
"""Unified Atlassian REST API client.

Usage:
    cli.py page         <domain-or-url> <pageId>
    cli.py lookup       <keyword> [<domain-or-url>]
    cli.py search       <domain-or-url> <query> [--space KEY]
    cli.py issue        <domain-or-url> <issueKey>
    cli.py jql          <domain-or-url> <query>
    cli.py add-comment  <domain-or-url> <issueKey> <body>
    cli.py get          <url>
    cli.py upload       <domain-or-url> <pageId> <file>
    cli.py token        {list|set|remove|test} [args...]
"""
import json
import os
import sys

# Ensure scripts/ is on path for sibling imports.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cache
import client
import convert
import tokens
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen


def die(msg):
    """Print error and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def extract_domain(s):
    """Extract domain from URL or bare domain string."""
    if s.startswith("http://") or s.startswith("https://"):
        return s.split("/")[2]
    return s


# --- Commands ---

def cmd_page(domain, page_id):
    """Fetch page with cache-aware update check."""
    meta_url = f"https://{domain}/rest/api/content/{page_id}?expand=version"
    meta = client.request(meta_url, domain)
    title = meta.get("title", "")
    ver = meta.get("version", {})
    version = ver.get("number", 0)
    author = ver.get("by", {}).get("displayName", "")
    updated = ver.get("when", "")

    cached_meta = cache.get_meta(domain, page_id)
    cached_text = cache.read_page(domain, page_id)

    if cached_meta and cached_text and cached_meta.get("updated") == updated:
        text = cached_text
    else:
        full_url = (f"https://{domain}/rest/api/content/{page_id}"
                    f"?expand=body.storage,version")
        full = client.request(full_url, domain)
        body_html = full.get("body", {}).get("storage", {}).get("value", "")
        text = convert.html2text(body_html, domain, page_id)
        cache.write_page(domain, page_id, text)
        cache.set_meta(domain, page_id, title, version, author, updated)

    print(f"title: {title}")
    print(f"version: {version}")
    print(f"author: {author}")
    print(f"updated: {updated}")
    print("=" * 60)
    print(text)


def cmd_lookup(keyword, domain=None):
    """Search local page index by keyword."""
    for pid, title in cache.search_index(keyword, domain):
        print(f"{pid}  {title}")


def cmd_search(domain, query, space=None):
    """Search Confluence via CQL."""
    cql = f'type=page AND text~"{query}"'
    if space:
        cql = f"space={space} AND {cql}"
    from urllib.parse import quote
    url = (f"https://{domain}/rest/api/content/search"
           f"?cql={quote(cql)}&limit=10")
    data = client.request(url, domain)
    pages = []
    for r in data.get("results", []):
        pid = str(r.get("id", ""))
        title = r.get("title", "")
        pages.append((pid, title))
        print(f"{pid}  {title}")
    cache.update_titles(domain, pages)


def cmd_issue(domain, key):
    """Fetch a Jira issue."""
    url = (f"https://{domain}/rest/api/2/issue/{key}"
           f"?fields=summary,status,description,assignee,priority,labels")
    print(json.dumps(client.request(url, domain), indent=2, ensure_ascii=False))


def cmd_add_comment(domain, key, body):
    """Add comment to a Jira issue."""
    url = f"https://{domain}/rest/api/2/issue/{key}/comment"
    result = client.request(url, domain, method="POST", data={"body": body})
    print(f"Comment added to {key} (id: {result['id']})")


def cmd_jql(domain, query):
    """Search Jira via JQL."""
    from urllib.parse import quote
    url = (f"https://{domain}/rest/api/2/search"
           f"?jql={quote(query)}&maxResults=20"
           f"&fields=summary,status,assignee,priority")
    print(json.dumps(client.request(url, domain), indent=2, ensure_ascii=False))


def cmd_get(url):
    """Raw GET to any Atlassian URL."""
    domain = extract_domain(url)
    print(client.request(url, domain, raw=True))


def cmd_upload(domain, page_id, file_path):
    """Update a Confluence page with Storage format HTML."""
    url = (f"https://{domain}/rest/api/content/{page_id}"
           f"?expand=version,title")
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


def cmd_token(args):
    """Manage Bearer tokens per domain."""
    sub = args[0] if args else ""
    if sub == "list":
        for d in tokens.list_domains():
            print(d)
    elif sub == "set":
        if len(args) < 3:
            die("Usage: token set <domain> <pat>")
        tokens.set_(args[1], args[2])
        print(f"Token set for {args[1]}")
    elif sub == "remove":
        if len(args) < 2:
            die("Usage: token remove <domain>")
        tokens.remove(args[1])
        print(f"Removed token for {args[1]}")
    elif sub == "test":
        if len(args) < 2:
            die("Usage: token test <domain>")
        domain = args[1]
        tok = tokens.get(domain)
        if not tok:
            die(f"No token for {domain}")
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


# --- CLI parsing ---

def parse_option(args, name):
    """Extract --name value from args, return (value, remaining)."""
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            die(f"{name} requires a value")
        return args[i + 1], args[:i] + args[i + 2:]
    return None, args


if __name__ == "__main__":
    if len(sys.argv) < 2:
        die("Usage: cli.py <command> [args...]")

    cmd = sys.argv[1]
    rest = sys.argv[2:]
    space_opt, rest = parse_option(rest, "--space")

    if cmd == "page":
        if len(rest) < 2:
            die("Usage: page <domain-or-url> <pageId>")
        cmd_page(extract_domain(rest[0]), rest[1])
    elif cmd == "lookup":
        if not rest:
            die("Usage: lookup <keyword> [<domain-or-url>]")
        domain = extract_domain(rest[1]) if len(rest) > 1 else None
        cmd_lookup(rest[0], domain)
    elif cmd == "search":
        if len(rest) < 2:
            die("Usage: search <domain-or-url> <query> [--space KEY]")
        cmd_search(extract_domain(rest[0]), rest[1], space_opt)
    elif cmd == "issue":
        if len(rest) < 2:
            die("Usage: issue <domain-or-url> <issueKey>")
        cmd_issue(extract_domain(rest[0]), rest[1])
    elif cmd == "jql":
        if len(rest) < 2:
            die("Usage: jql <domain-or-url> <query>")
        cmd_jql(extract_domain(rest[0]), rest[1])
    elif cmd == "add-comment":
        if len(rest) < 3:
            die("Usage: add-comment <domain-or-url> <issueKey> <body>")
        cmd_add_comment(extract_domain(rest[0]), rest[1], rest[2])
    elif cmd == "get":
        if not rest:
            die("Usage: get <url>")
        cmd_get(rest[0])
    elif cmd == "upload":
        if len(rest) < 3:
            die("Usage: upload <domain-or-url> <pageId> <file>")
        cmd_upload(extract_domain(rest[0]), rest[1], rest[2])
    elif cmd == "token":
        cmd_token(rest)
    else:
        die(f"Unknown command: {cmd}")
