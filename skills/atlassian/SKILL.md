---
name: atlassian
description: "Atlassian Personal Access Token (PAT) management, Confluence page caching with full-text search, and live Jira issue fetching. Use when you need to store or retrieve a PAT for an Atlassian domain, cache and search Confluence pages, fetch a Jira issue, or hand an Atlassian URL to the agent and let it dispatch automatically. Trigger on: 'token', 'PAT', '401', '403', Atlassian URL (including /pages/, /display/, /wiki/, /browse/), Confluence page caching, Jira issue lookup, '令牌', '缓存页面', '抓取', 'Confluence 页面', 'Jira issue'. This skill does NOT wrap standard Atlassian API calls (creating or editing pages, JQL, CQL, bulk operations); for those, the agent writes Python against atlassian-python-api directly using the PAT from this skill's local store (see references/client_setup.py)."
---

# atlassian-api

PAT management plus high-frequency Atlassian operations: Confluence
page caching with FTS5 search, and live Jira issue fetching. For
anything else, write Python against `atlassian-python-api` directly.

## CLI

```
scripts/cli.py <command> [args...]
```

### `fetch <url>` — primary entry

Classify any Atlassian URL and dispatch automatically:

```
scripts/cli.py fetch <url> [--format text|json|html] [--refresh] [--full]
```

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

### Token management

```
scripts/cli.py token list
scripts/cli.py token set    <domain> <pat>
scripts/cli.py token remove <domain>
scripts/cli.py token test   <domain>
```

No `token get` — PATs must not be echoed to stdout.

## For operations NOT covered above

For writes, JQL, CQL, bulk operations, custom fields, etc., write
Python against `atlassian-python-api` using the PAT from this skill.
Read `references/client_setup.py` for a copy-pasteable template.

Key rules:
1. PAT stays inside the Python process — never print or pass via shell args
2. Use `atlassian-python-api`, not raw `requests`
3. Keep scripts narrow and task-specific

## Data

SQLite at `$KIRO_HOME/data/atlassian/atlassian.db` (mode `0600`). Override with `ATLASSIAN_API_DB` env var.

Tables: `tokens`, `confluence_pages` (body cache), `confluence_pages_fts` (FTS5).

## Dependencies

- Python 3.10+
- `atlassian-python-api>=3.41,<4`
