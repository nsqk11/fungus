---
name: atlassian-api
description: "Atlassian token management and Confluence page caching. Use when managing PATs, fetching cached pages, or searching local page index. Trigger on mentions of 'token', 'PAT', '401', '403', 'page cache', or 'lookup'. For all other Confluence/Jira API calls, use atlassian-python-api library directly. Do NOT wrap standard API calls — agent calls the library."
---

# atlassian-api

> Manage Atlassian tokens and provide cached Confluence page access.

## Boundary

- **Does**:
  - Store and retrieve Bearer tokens per domain in SQLite.
  - Fetch Confluence pages with version-based incremental caching.
  - Convert Storage HTML to plain text with image download links.
  - Search local page cache by keyword.
- **Does not**:
  - Wrap standard Confluence/Jira API calls — agent uses `atlassian-python-api` directly.
  - Auto-renew expired tokens.
  - Download or cache images.

## Interface

- **Entry**: `python3.12 cli.py <command> [args...]`
- **Commands**: `token`, `page`, `lookup`
- **Help**: `python3.12 cli.py --help` or `python3.12 cli.py <command> --help`
- **Output**: stdout (text or JSON). Data in `data/store.db`.
- **Dependency**: `atlassian-python-api`

## Behavior

Run `python3.12 cli.py --help` for command usage.

### Design decisions

- **Token storage**: single SQLite database at `data/store.db`, file permissions 600.
- **Page caching**: lightweight metadata check first; full fetch only when content changed.
- **Library delegation**: standard API calls are not wrapped. Agent calls `atlassian-python-api` directly.

## Library Direct Usage

For all standard Confluence/Jira API calls, use `atlassian-python-api` library directly.

- **Token**: `python3.12 cli.py token get <domain>`
- **Discover methods**: `python3.12 -c "from atlassian import Confluence; help(Confluence.<method>)"`
- **Documentation**: https://atlassian-api.readthedocs.io
