---
name: atlassian-api
description: "[tool] Unified Atlassian REST API client — Confluence pages, Jira issues, token management, local content caching, page analytics, page comments. Use when making REST API calls to any Confluence or Jira instance. Trigger on mentions of 'Atlassian REST API', 'Confluence page', 'Jira issue', 'PAT', 'token', '401', '403', 'page viewers', 'analytics', 'who viewed', or 'comments'. Do NOT use for business logic — that belongs to calling skills."
---

# atlassian-api

> Unified CLI for Atlassian Confluence and Jira REST APIs with token management and local caching.

## Boundary

- **Does**:
  - Send authenticated REST requests to Confluence and Jira.
  - Manage Bearer tokens per domain.
  - Fetch and cache Confluence pages with update check.
  - Search Confluence via CQL and Jira via JQL.
  - Upload Confluence page content with auto version increment.
  - Convert Storage HTML to plain text with image download links.
  - Fetch page view analytics (who viewed, view count).
  - Fetch page comments (regular and inline).
- **Does not**:
  - Contain business logic — calling skills decide what to fetch and how to use it.
  - Auto-renew expired tokens — user must create new PATs manually.
  - Access non-Atlassian APIs.
  - Download or cache images.

## Interface

- **Entry**: `python3 cli.py <command> [args...]`
- **Help**: `python3 cli.py --help` or `python3 cli.py <command> --help`
- **Commands**: `page`, `lookup`, `search`, `issue`, `jql`, `add-comment`, `get`, `upload`, `analytics`, `get-comments`, `token`
- **Input**: CLI arguments. First argument is domain or URL for network commands.
- **Output**: stdout (text or JSON). Data in `data/` (tokens, page index, page cache).

## Behavior

Run `python3 cli.py --help` for command usage.

### Design decisions

- **Domain resolution**: first argument is domain or full URL; domain extracted automatically.
- **Page caching**: lightweight metadata check first; full fetch only when content changed.
- **Image conversion**: attachment images converted to full `download/attachments/` URLs, not cached.
- **Storage**: single SQLite database at `data/store.db`, file permissions 600. Tables: `tokens` (domain → PAT) and `cache` (domain + page_id → metadata + content).
- **Analytics auth**: confanalytics API accepts PAT Bearer auth directly — no session cookie needed.
