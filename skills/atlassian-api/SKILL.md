---
name: atlassian-api
description: "[tool] Unified Atlassian REST API client — Confluence pages, Jira issues, token management, local content caching. Use when making REST API calls to any Confluence or Jira instance. Trigger on mentions of 'Atlassian REST API', 'Confluence page', 'Jira issue', 'PAT', 'token', '401', or '403'. Do NOT use for business logic — that belongs to calling skills."
---

# atlassian-api

> Unified CLI for Atlassian Confluence and Jira REST APIs with token management and local caching.

## Boundary

- **Does**:
  - Send authenticated REST requests to Confluence and Jira.
  - Manage Bearer tokens per domain.
  - Fetch Confluence pages with cache-aware update check.
  - Cache page content as plain text per domain.
  - Search Confluence via CQL and Jira via JQL.
  - Upload Confluence page content with auto version increment.
  - Convert Storage HTML to plain text with image download links.
- **Does not**:
  - Contain business logic — calling skills decide what to fetch and how to use it.
  - Auto-renew expired tokens — user must create new PATs manually.
  - Access non-Atlassian APIs.
  - Download or cache images.

## Interface

- **Entry**: `python3 cli.py <command> [args...]`
- **Help**: `python3 cli.py --help` or `python3 cli.py <command> --help`
- **Commands**: `page`, `lookup`, `search`, `issue`, `jql`, `add-comment`, `get`, `upload`, `token`
- **Input**: CLI arguments. First argument is domain or URL for network commands.
- **Output**: stdout (text or JSON). Data in `data/` (tokens, page index, page cache).

## Behavior

Run `python3 cli.py --help` for command usage.

### Design decisions

- **Domain resolution**: first argument is domain or full URL; domain extracted automatically.
- **page caching**: lightweight metadata check first; full fetch only when content changed.
- **Image conversion**: attachment images converted to full `download/attachments/` URLs, not cached.
- **Cache structure**: `data/pages/<domain>/<pageId>.txt`, index at `data/page-index.json` keyed by domain.
- **Token storage**: `data/tokens.json`, file permissions 600.
