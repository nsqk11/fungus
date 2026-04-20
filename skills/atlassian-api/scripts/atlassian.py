#!/usr/bin/env python3
"""Unified Atlassian REST API client.

Usage:
    atlassian.py page <pageId>
    atlassian.py lookup <keyword>
    atlassian.py search <query> [--space SPACEKEY]
    atlassian.py issue <issueKey>
    atlassian.py jql <query>
    atlassian.py add-comment <issueKey> <body>
    atlassian.py get <url>
    atlassian.py upload <pageId> <file.storage.html>
    atlassian.py token {list|set|remove|test} [args...]

Environment:
    ATLASSIAN_CONFLUENCE  Confluence domain (e.g. wiki.example.com)
    ATLASSIAN_JIRA        Jira domain (e.g. jira.example.com)
"""
import sys, os, json, re, html, subprocess
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KVSTORE = os.path.join(SCRIPT_DIR, "kvstore.sh")
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
TOKENS = os.path.join(DATA_DIR, "tokens.json")
INDEX = os.path.join(DATA_DIR, "page-index.json")
PAGES_DIR = os.path.join(DATA_DIR, "pages")

CONFLUENCE = os.environ.get("ATLASSIAN_CONFLUENCE", "")
JIRA = os.environ.get("ATLASSIAN_JIRA", "")


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def require_confluence():
    if not CONFLUENCE:
        die("ATLASSIAN_CONFLUENCE not set")
    return CONFLUENCE


def require_jira():
    if not JIRA:
        die("ATLASSIAN_JIRA not set")
    return JIRA


def kv(file, cmd, key="", val=""):
    args = ["bash", KVSTORE, file, cmd]
    if key:
        args.append(key)
    if val:
        args.append(val)
    r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.stdout.decode().strip()


def get_token(domain):
    tok = kv(TOKENS, "get", domain)
    if not tok:
        die(f"No token for {domain}")
    return tok


def http_request(url, domain, method="GET", data=None):
    token = get_token(domain)
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode() if isinstance(data, dict) else data
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 401:
            die(f"401 Unauthorized — token for {domain} may be expired.")
        elif e.code == 403:
            die(f"403 Forbidden — no permission or token lacks scope.")
        else:
            die(f"HTTP {e.code} from {url}")


def http_get_raw(url, domain):
    token = get_token(domain)
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(req) as resp:
            return resp.read().decode()
    except HTTPError as e:
        die(f"HTTP {e.code} from {url}")


def html2text(h):
    t = re.sub(r'<br\s*/?>', '\n', h)
    t = re.sub(r'</?(p|div|li|tr|td|th|h[1-6])[^>]*>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


# --- Page index (object-value format) ---

def index_read():
    if not os.path.exists(INDEX):
        return {}
    with open(INDEX) as f:
        return json.load(f)


def index_write(idx):
    with open(INDEX, "w") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)


def index_set(page_id, title, version, author, updated):
    idx = index_read()
    idx[str(page_id)] = {
        "title": title,
        "version": version,
        "author": author,
        "updated": updated,
    }
    index_write(idx)


# --- Commands ---

def cmd_page(page_id):
    domain = require_confluence()
    url = (f"https://{domain}/rest/api/content/{page_id}"
           f"?expand=body.storage,version")
    data = http_request(url, domain)
    title = data.get("title", "")
    ver = data.get("version", {})
    version = ver.get("number", 0)
    author = ver.get("by", {}).get("displayName", "")
    updated = ver.get("when", "")
    body_html = data.get("body", {}).get("storage", {}).get("value", "")
    text = html2text(body_html)

    index_set(page_id, title, version, author, updated)

    os.makedirs(PAGES_DIR, exist_ok=True)
    with open(os.path.join(PAGES_DIR, f"{page_id}.txt"), "w") as f:
        f.write(text)

    print(f"title: {title}")
    print(f"version: {version}")
    print(f"author: {author}")
    print(f"updated: {updated}")
    print("=" * 60)
    print(text)


def cmd_lookup(keyword):
    idx = index_read()
    kw = keyword.lower().split()
    for pid, meta in idx.items():
        title = meta.get("title", "") if isinstance(meta, dict) else str(meta)
        if all(w in title.lower() for w in kw):
            print(f"{pid}  {title}")


def cmd_search(query, space=None):
    domain = require_confluence()
    cql = f'type=page AND text~"{query}"'
    if space:
        cql = f"space={space} AND {cql}"
    url = (f"https://{domain}/rest/api/content/search"
           f"?cql={quote(cql)}&limit=10")
    data = http_request(url, domain)
    idx = index_read()
    for r in data.get("results", []):
        pid = str(r.get("id", ""))
        title = r.get("title", "")
        idx[pid] = idx.get(pid, {"title": title})
        idx[pid]["title"] = title
        print(f"{pid}  {title}")
    index_write(idx)


def cmd_issue(key):
    domain = require_jira()
    url = (f"https://{domain}/rest/api/2/issue/{key}"
           f"?fields=summary,status,description,assignee,priority,labels")
    print(json.dumps(http_request(url, domain), indent=2, ensure_ascii=False))


def cmd_add_comment(key, body):
    domain = require_jira()
    url = f"https://{domain}/rest/api/2/issue/{key}/comment"
    result = http_request(url, domain, method="POST", data={"body": body})
    print(f"Comment added to {key} (id: {result['id']})")


def cmd_jql(query):
    domain = require_jira()
    url = (f"https://{domain}/rest/api/2/search"
           f"?jql={quote(query)}&maxResults=20"
           f"&fields=summary,status,assignee,priority")
    print(json.dumps(http_request(url, domain), indent=2, ensure_ascii=False))


def cmd_get(url):
    domain = url.split("/")[2]
    print(http_get_raw(url, domain))


def cmd_upload(page_id, file_path):
    domain = require_confluence()
    url = (f"https://{domain}/rest/api/content/{page_id}"
           f"?expand=version,title")
    data = http_request(url, domain)
    ver = data["version"]["number"]
    title = data["title"]
    body = open(file_path).read()
    payload = {
        "id": page_id, "type": "page", "title": title,
        "body": {"storage": {"value": body, "representation": "storage"}},
        "version": {"number": ver + 1},
    }
    result = http_request(url, domain, method="PUT", data=payload)
    print(f"OK — {title} updated to version {result['version']['number']}")


def cmd_token(args):
    sub = args[0] if args else ""
    if sub == "list":
        print(kv(TOKENS, "list"))
    elif sub == "set":
        if len(args) < 3:
            die("Usage: token set <domain> <pat>")
        kv(TOKENS, "set", args[1], args[2])
        print(f"Token set for {args[1]}")
    elif sub == "remove":
        if len(args) < 2:
            die("Usage: token remove <domain>")
        kv(TOKENS, "remove", args[1])
        print(f"Removed token for {args[1]}")
    elif sub == "test":
        if len(args) < 2:
            die("Usage: token test <domain>")
        domain = args[1]
        token = get_token(domain)
        for endpoint in [
            f"https://{domain}/rest/api/content?limit=1",
            f"https://{domain}/rest/api/2/serverInfo",
        ]:
            req = Request(endpoint,
                          headers={"Authorization": f"Bearer {token}"})
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        die("Usage: atlassian.py <command> <arg> [options]")

    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else ""

    if cmd == "page":
        arg or die("Usage: page <pageId>")
        cmd_page(arg)
    elif cmd == "lookup":
        arg or die("Usage: lookup <keyword>")
        cmd_lookup(arg)
    elif cmd == "search":
        arg or die("Usage: search <query> [--space X]")
        space = (sys.argv[4]
                 if len(sys.argv) > 4 and sys.argv[3] == "--space"
                 else None)
        cmd_search(arg, space)
    elif cmd == "issue":
        arg or die("Usage: issue <issueKey>")
        cmd_issue(arg)
    elif cmd == "jql":
        arg or die("Usage: jql <query>")
        cmd_jql(arg)
    elif cmd == "get":
        arg or die("Usage: get <url>")
        cmd_get(arg)
    elif cmd == "add-comment":
        arg or die("Usage: add-comment <issueKey> <body>")
        body = (sys.argv[3] if len(sys.argv) > 3
                else die("Usage: add-comment <issueKey> <body>"))
        cmd_add_comment(arg, body)
    elif cmd == "upload":
        arg or die("Usage: upload <pageId> <file>")
        f = (sys.argv[3] if len(sys.argv) > 3
             else die("Usage: upload <pageId> <file>"))
        cmd_upload(arg, f)
    elif cmd == "token":
        cmd_token(sys.argv[2:])
    else:
        die(f"Unknown command: {cmd}")
