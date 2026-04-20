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
  - Maintain a page index per domain.
  - Search Confluence via CQL and Jira via JQL.
  - Upload Confluence page content with auto version increment.
  - Convert Confluence Storage HTML to plain text with image links.
- **Does not**:
  - Contain business logic — calling skills decide what to fetch and how to use it.
  - Auto-renew expired tokens — user must create new PATs manually.
  - Access non-Atlassian APIs.
  - Download or cache images.

## Interface

- **Commands**:
  - `cli.py page` — fetch and cache a Confluence page.
  - `cli.py lookup` — search local page index.
  - `cli.py search` — Confluence CQL search.
  - `cli.py issue` — fetch a Jira issue.
  - `cli.py jql` — Jira JQL search.
  - `cli.py add-comment` — add comment to Jira issue.
  - `cli.py get` — raw GET to any Atlassian URL.
  - `cli.py upload` — update Confluence page content.
  - `cli.py token` — manage tokens (list/set/remove/test).
- **Input**: CLI arguments. First argument is domain or URL for network commands.
- **Output**: stdout (text or JSON). Tokens in `data/tokens.json`. Page cache in `data/pages/<domain>/`. Index at `data/page-index.json`.

## Behavior

### page

Fetch a Confluence page with cache-aware update check.

```bash
python3 cli.py page <domain-or-url> <pageId>
```

Process:
1. GET metadata (lightweight, no body).
2. Compare `updated` time with local index.
3. Changed → GET full content, convert HTML to text (with image links), update cache and index.
4. Unchanged → read local cache.
5. Print metadata header and text content.

Output: metadata header (`title`, `version`, `author`, `updated`) followed by plain text content.

### lookup

Search the local page index by keyword.

```bash
python3 cli.py lookup <keyword> [<domain-or-url>]
```

Process: all words in keyword must match the title (case-insensitive). Optional domain limits search scope.

Output: `pageId  title` per match, one per line.

### search

Search Confluence via CQL.

```bash
python3 cli.py search <domain-or-url> <query> [--space SPACEKEY]
```

Process: query Confluence CQL, return up to 10 results, update page index with titles.

Output: `pageId  title` per result, one per line.

### issue

Fetch a Jira issue.

```bash
python3 cli.py issue <domain-or-url> <issueKey>
```

Output: JSON with summary, status, description, assignee, priority, labels.

### jql

Search Jira via JQL.

```bash
python3 cli.py jql <domain-or-url> <query>
```

Output: up to 20 results as JSON.

### add-comment

Add a comment to a Jira issue.

```bash
python3 cli.py add-comment <domain-or-url> <issueKey> "<body>"
```

Output: confirmation message with comment ID.

### get

Raw GET request to any Atlassian URL. Domain extracted from URL for token lookup.

```bash
python3 cli.py get <url>
```

Output: raw response body.

### upload

Update a Confluence page with Storage format HTML.

```bash
python3 cli.py upload <domain-or-url> <pageId> <file.storage.html>
```

Process: read current version, increment by 1, PUT new content.

Output: confirmation message with new version number.

### token

Manage Bearer tokens per domain.

```bash
python3 cli.py token list
python3 cli.py token set <domain> <pat>
python3 cli.py token remove <domain>
python3 cli.py token test <domain>
```

Output: `list` prints configured domains. `set`/`remove` print confirmation. `test` prints OK, EXPIRED, or FAILED.
