---
name: atlassian-api
description: "Atlassian Personal Access Token (PAT) management, Confluence page caching with full-text search, and live Jira issue fetching. Use when you need to store or retrieve a PAT for an Atlassian domain, cache and search Confluence pages, fetch a Jira issue, or hand an Atlassian URL to the agent and let it dispatch automatically. Trigger on: 'token', 'PAT', '401', '403', Atlassian URL (including /pages/, /display/, /wiki/, /browse/), Confluence page caching, Jira issue lookup. This skill does NOT wrap standard Atlassian API calls (creating or editing pages, JQL, CQL, bulk operations); for those, the agent writes Python against atlassian-python-api directly using the PAT from this skill's local store (see references/client_setup.py)."
---

# atlassian-api

PAT management plus a small set of high-frequency Atlassian resource
operations: Confluence page caching with search, and live Jira issue
fetching. Everything else should be written by the agent using
`atlassian-python-api` directly.

## Scope

- **Does**
  - Store, list, remove, and test Personal Access Tokens per Atlassian
    domain in a local SQLite file (permissions `0600`).
  - Classify an Atlassian URL (standard path patterns only) and dispatch:
    Confluence pages go through a version-aware cache; Jira issues are
    fetched live.
  - Full-text search (FTS5) across cached Confluence pages.
  - Prime a Confluence space's title index with `sync`.
- **Does not**
  - Wrap the rest of the Atlassian API. For writes, JQL, CQL, bulk
    operations, custom field queries, etc., the agent writes Python
    against `atlassian-python-api` using the PAT from this skill.
  - Cache Jira issues. Jira state changes too often for caching to be
    useful; always fetch live.
  - Auto-renew expired tokens. Detect expiry and surface it to the user
    via `token test`.
  - Download page attachments. Image references are preserved as
    `[image: url]` placeholders only.

## Entry points

Run scripts from the skill directory. The primary interface is the CLI:

```
python3.12 scripts/cli.py <command> [args...]
python3.12 scripts/cli.py --help
python3.12 scripts/cli.py <command> --help
```

### `fetch <url>` — primary entry

Hand the skill any Atlassian URL; it will classify and dispatch:

```
python3.12 scripts/cli.py fetch <url>
python3.12 scripts/cli.py fetch <url> --format json
python3.12 scripts/cli.py fetch <url> --refresh          # force re-fetch
python3.12 scripts/cli.py fetch <url> --full             # all Jira comments
```

Supported URL patterns (no hardcoded domains; path-based):

- **Confluence pages**: `/pages/<id>`, `/pages/viewpage.action?pageId=<id>`,
  `/spaces/<SPACE>/pages/<id>`, `/display/<SPACE>/<Title>`, `/wiki/...`
- **Jira issues**: `/browse/<KEY>-<N>`

### Explicit entry points

When you already know the kind of resource:

```
python3.12 scripts/cli.py page  <domain> <pageId>   [--format text|json|html] [--refresh]
python3.12 scripts/cli.py issue <domain> <issueKey> [--format text|json]      [--full]
```

### Search and sync

```
python3.12 scripts/cli.py search <query> [--domain <d>] [--title-only] [--limit N]
python3.12 scripts/cli.py sync   <domain> <spaceKey>
```

`search` runs FTS5 over cached `title + body_text`. `sync` pulls page
metadata (title + version, no body) for every page in a Confluence space
so that title searches find pages that haven't been individually fetched.

### Token management

```
python3.12 scripts/cli.py token list
python3.12 scripts/cli.py token set    <domain> <pat>
python3.12 scripts/cli.py token remove <domain>
python3.12 scripts/cli.py token test   <domain>
```

`token list` shows each domain with its last-tested timestamp and status
(`ok` / `expired` / `unknown`). There is deliberately no `token get`:
PATs must not be echoed to stdout. See the next section.

## When NOT to use this skill — write your own API code

For anything outside the commands above (create/edit/delete pages, run
JQL or CQL, bulk operations, custom fields, comments, attachments, …),
the agent should **write Python directly** against `atlassian-python-api`,
using the PAT from this skill's local store.

Read **`references/client_setup.py`** for a copy-pasteable template. The
key pattern:

```python
# Inside the agent's Python process — PAT stays in memory
import sqlite3
from pathlib import Path
from atlassian import Confluence, Jira

DB = Path("<skill-dir>/data/store.db")
domain = "example.atlassian.net"
pat = sqlite3.connect(DB).execute(
    "SELECT pat FROM tokens WHERE domain = ?", (domain,)
).fetchone()[0]

confluence = Confluence(url=f"https://{domain}", token=pat)
jira = Jira(url=f"https://{domain}", token=pat)

# Now call any atlassian-python-api method directly.
confluence.create_page(space="DEV", title="Hello", body="<p>Hi</p>")
results = jira.jql("project = PROJ AND status = Open")
```

**Do not**:
- Write raw `requests` calls to Atlassian REST endpoints. Use
  `atlassian-python-api`; it handles auth, pagination, and error shape.
- Print the PAT to stdout or pass it through shell arguments. Read it
  inside the Python process only.
- Extend this skill to wrap common API operations. Keep the skill small;
  write the specific code the task needs.

### Discovering library methods

```python
from atlassian import Confluence, Jira
help(Confluence.create_page)
help(Jira.issue)
```

Docs: <https://atlassian-python-api.readthedocs.io>

## Data layout

One SQLite file at `data/store.db`, mode `0600`:

- `tokens` — `(domain, pat, created_at, last_tested, status)`
- `confluence_pages` — page body cache with `version` + `body_html` +
  `body_text`
- `confluence_pages_fts` — FTS5 virtual table indexed on `title` and
  `body_text`

Override the path with the `ATLASSIAN_API_DB` environment variable.

## Dependencies

- Python 3.12+
- `atlassian-python-api>=3.41,<4` (install via the repository's
  `install.sh`, which runs `pip install --user atlassian-python-api`)

## Design decisions

- **Single SQLite file** keeps deployment trivial and makes cross-table
  queries easy. Concurrent access is not a design goal.
- **Store raw HTML and derived text** so the text projection can be
  rebuilt without re-fetching when the conversion logic changes.
- **No `token get` CLI**: PAT must not leave the Python process.
- **Jira not cached**: state drift outweighs cache savings.
- **URL classification is path-based only**: no hardcoded hosts; the
  skill works with any Atlassian Data Center or Cloud deployment.
