# atlassian-api

A small Fungus skill that manages Atlassian Personal Access Tokens and
provides a handful of high-frequency Atlassian operations:

- **Token management** — store, list, test, and remove PATs per
  Atlassian domain. Tokens live in a local SQLite file with mode `0600`.
- **Confluence page caching** — version-aware incremental fetch with
  FTS5 full-text search over cached pages.
- **Jira issue fetching** — live fetch (no caching) of a single issue by
  key, with human-readable or JSON output.
- **Smart URL dispatch** — hand the skill any Atlassian URL and it
  classifies the resource (Confluence page or Jira issue) and dispatches.

Everything outside this narrow scope (creating or editing pages, JQL, CQL,
bulk operations, custom fields) is out of scope. The agent calls
[`atlassian-python-api`](https://atlassian-python-api.readthedocs.io)
directly for those; see `references/client_setup.py` for the pattern.

## Requirements

- Python 3.12+
- `atlassian-python-api>=3.41,<4`

Install the dependency with:

```bash
pip install --user -r requirements.txt
```

If you are running this inside Fungus, the repository-level `install.sh`
handles this for you.

## Quickstart

```bash
# 1. Store a PAT for your Atlassian host (no hardcoded domains — you supply it)
python3.12 scripts/cli.py token set example.atlassian.net <your-pat>

# 2. Verify the token works
python3.12 scripts/cli.py token test example.atlassian.net

# 3. Fetch a Confluence page by URL (auto-cached)
python3.12 scripts/cli.py fetch https://example.atlassian.net/wiki/spaces/DEV/pages/12345

# 4. Fetch a Jira issue by URL (live)
python3.12 scripts/cli.py fetch https://example.atlassian.net/browse/PROJ-1

# 5. Full-text search across cached pages
python3.12 scripts/cli.py search "deployment guide"

# 6. Prime a space's title index so title searches work before individual
#    pages have been fetched
python3.12 scripts/cli.py sync example.atlassian.net DEV
```

## Commands

Run `python3.12 scripts/cli.py <command> --help` for full usage.

| Command | Purpose |
|---|---|
| `fetch <url>` | Classify an Atlassian URL and dispatch to cache or live fetch |
| `page <domain> <pageId>` | Fetch a specific Confluence page (cached) |
| `issue <domain> <key>` | Fetch a specific Jira issue (live) |
| `search <query>` | FTS5 search over cached Confluence pages |
| `sync <domain> <space>` | Prime title index for all pages in a space |
| `token list` | Show stored tokens with last-tested status |
| `token set <domain> <pat>` | Store or update a PAT |
| `token test <domain>` | Probe a PAT against the server |
| `token remove <domain>` | Delete a PAT |

Flags worth knowing:

- `fetch`/`page`: `--format text|json|html`, `--refresh` to force
  re-download, `--full` to print all Jira comments.
- `search`: `--domain <d>` to limit scope, `--title-only` for title
  search, `--limit N`.

## Data layout

Everything lives in `data/store.db` (created on first use):

- `tokens(domain, pat, created_at, last_tested, status)`
- `confluence_pages(domain, page_id, title, space_key, version, author,
  updated_at, fetched_at, body_html, body_text)`
- `confluence_pages_fts` — FTS5 virtual table over `title` and
  `body_text`

Set `ATLASSIAN_API_DB=/path/to/custom.db` to override the location.

## Extending

For anything outside the built-in commands, write Python directly using
`atlassian-python-api`:

```python
import sqlite3
from atlassian import Confluence

DB = "skills/atlassian-api/data/store.db"
pat = sqlite3.connect(DB).execute(
    "SELECT pat FROM tokens WHERE domain = ?", ("example.atlassian.net",),
).fetchone()[0]

c = Confluence(url="https://example.atlassian.net", token=pat)
c.create_page(space="DEV", title="Hello", body="<p>Hi</p>")
```

See `references/client_setup.py` for a more complete template.

## Security notes

- The SQLite file is chmod `0600`. Treat the file as sensitive.
- There is deliberately no CLI subcommand that prints a PAT to stdout.
  Read tokens from Python inside your own script so the PAT stays in
  process memory.
- The skill makes outbound network requests only to hosts you explicitly
  configure via `token set`. It does not contact any third-party
  services.

## License

Same as the parent repository (see repository root `LICENSE`).
