---
name: atlassian
description: "Atlassian PAT management, Confluence page caching with full-text search, and live Jira issue fetching. Use whenever the user mentions Atlassian, Confluence, Jira, or pastes an Atlassian URL. Also use when encountering 401/403 errors against Atlassian hosts, when the user wants to look up a wiki page or issue, or needs to search across cached documentation. For writes, JQL, CQL, or bulk operations, use the PAT from this skill's store with atlassian-python-api directly."
compatibility: "Python 3.10+, atlassian-python-api>=3.41"
---

# Atlassian

PAT management plus high-frequency Atlassian operations: Confluence
page caching with FTS5 search, and live Jira issue fetching. For
anything else, write Python against `atlassian-python-api` directly
using the template in [references/client_setup.py](references/client_setup.py).

## Getting started

Install the dependency (one-time):

```
pip install -r requirements.txt
```

Then store a PAT (must be done before any fetch/page/issue/search):

```
scripts/cli.py token set example.atlassian.net <pat>
scripts/cli.py token test example.atlassian.net
```

If `token test` prints `ok`, you're ready. If it prints `expired`, the
PAT needs to be regenerated on the Atlassian side and re-stored with
`token set`.

## CLI

All commands are invoked via:

```
scripts/cli.py <command> [args...]
```

### `fetch <url>` — primary entry

Classify any Atlassian URL and dispatch automatically:

```
scripts/cli.py fetch <url> [--format text|json|html] [--refresh] [--full]
```

- Default format: `text`
- `--refresh`: force re-download even if cached (Confluence only)
- `--full`: print all Jira comments (default: last 10)
- `--format html`: Confluence only, returns raw Storage format HTML

Supported URL patterns (path-based, no hardcoded domains):
- Confluence: `/pages/<id>`, `/viewpage.action?pageId=<id>`, `/display/<SPACE>/<Title>`, `/wiki/...`
- Jira: `/browse/<KEY>-<N>`

### Explicit commands

```
scripts/cli.py page  <domain> <pageId>   [--format text|json|html] [--refresh]
scripts/cli.py issue <domain> <issueKey> [--format text|json] [--full]
scripts/cli.py search <query> [--domain <d>] [--title-only] [--limit N]
scripts/cli.py sync   <domain> <spaceKey>
```

- `page`: fetches and caches a Confluence page. Returns cached version unless `--refresh`.
- `issue`: live fetch every time (no caching). Default shows last 10 comments; `--full` shows all.
- `search`: FTS5 search over **previously cached** pages only. Pages must have been fetched at least once to appear in results. Use `--title-only` for title-only search. Default limit: 50.
- `sync`: fetches title index for all pages in a space (no body content). Enables title search before individual pages are fetched.

### Token management

```
scripts/cli.py token list
scripts/cli.py token set    <domain> <pat>
scripts/cli.py token remove <domain>
scripts/cli.py token test   <domain>
```

No `token get` — PATs must not be echoed to stdout.

## Examples

**Fetch a Confluence page by URL:**
```
$ scripts/cli.py fetch https://example.atlassian.net/wiki/spaces/DEV/pages/12345
# Deployment Guide
Space: DEV | Version: 14 | Author: alice | Updated: 2025-01-15T10:30:00Z

This document describes the deployment process...
```

**Fetch a Jira issue:**
```
$ scripts/cli.py issue example.atlassian.net PROJ-42 --format text
PROJ-42: Fix login timeout
Status: In Progress | Assignee: alice | Priority: High
Created: 2025-01-10 | Updated: 2025-01-14

Description:
  Users report timeout after 30s on the login page...

Comments (showing last 10):
  [2025-01-12 bob]: Reproduced on staging...
  [2025-01-13 alice]: Root cause identified...
```

**Fetch as JSON (for programmatic use):**
```
$ scripts/cli.py issue example.atlassian.net PROJ-42 --format json
{"key": "PROJ-42", "summary": "Fix login timeout", "status": "In Progress", ...}
```

**Search cached pages:**
```
$ scripts/cli.py search "deployment guide" --limit 5
example.atlassian.net       12345  Deployment Guide
example.atlassian.net       67890  CI/CD Deployment Pipeline
```

**Token management:**
```
$ scripts/cli.py token list
DOMAIN                        STATUS      LAST_TESTED
example.atlassian.net         ok          2025-01-15T08:00:00Z
```

## Error handling

All errors print to stderr with an `ERROR:` prefix and return exit code 1.

| Situation | Error message |
|-----------|--------------|
| No token stored for domain | `No token stored for <domain>` |
| Token expired/invalid | `token test` returns `expired` |
| Unrecognised URL pattern | `Unrecognised Atlassian URL: <url>. Supported path patterns: ...` |
| Cannot extract page ID from URL | `Could not extract a page id from <url>; use 'page <domain> <pageId>' directly.` |
| `--format html` on Jira issue | `--format html is not supported for Jira issues` |
| Network/API error | Exception message from atlassian-python-api (HTTP status + body) |

**Recovery steps:**
- 401/403 → run `token test`; if expired, get a new PAT and `token set`
- Page not found → verify the page ID exists; it may have been deleted or moved
- Search returns nothing → the page hasn't been cached yet; `fetch` it first, or `sync` the space

## Edge cases

- URLs with query parameters (e.g. `?focusedId=...`) are handled; only the page ID is extracted.
- `search` only finds pages that have been previously fetched or synced. A freshly set-up skill with no cache returns no results.
- `sync` fetches titles only (lightweight). To get full body content for search, fetch individual pages.
- Multiple domains are supported simultaneously. Each domain needs its own `token set`.
- Domain names are normalised (lowercased, trailing slashes stripped).

## For operations NOT covered above

For writes, JQL, CQL, bulk operations, custom fields, etc., write
Python against `atlassian-python-api` using the PAT from this skill.
See [references/client_setup.py](references/client_setup.py) for a
copy-pasteable template.

Key rules:
1. PAT stays inside the Python process — never print or pass via shell args
2. Use `atlassian-python-api`, not raw `requests`
3. Keep scripts narrow and task-specific

## Data

SQLite at `$KIRO_HOME/data/atlassian/atlassian.db` (mode `0600`).
Override with `ATLASSIAN_API_DB` env var.

Tables: `tokens`, `confluence_pages` (body cache), `confluence_pages_fts` (FTS5).
