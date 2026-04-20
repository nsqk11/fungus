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
  - Fetch Confluence pages with version, author, and updated metadata.
  - Cache page content as plain text to `data/pages/<pageId>.txt`.
  - Maintain a page index at `data/page-index.json`.
  - Search Confluence via CQL and Jira via JQL.
  - Upload Confluence page content with auto version increment.
  - Convert Confluence Storage HTML to plain text.
- **Does not**:
  - Contain business logic — calling skills decide what to fetch and how to use it.
  - Auto-renew expired tokens — user must create new PATs manually.
  - Access non-Atlassian APIs.

## Interface

- **Commands**:
  - `atlassian.py page` — fetch and cache a Confluence page.
  - `atlassian.py lookup` — search local page index.
  - `atlassian.py search` — Confluence CQL search.
  - `atlassian.py issue` — fetch a Jira issue.
  - `atlassian.py jql` — Jira JQL search.
  - `atlassian.py add-comment` — add comment to Jira issue.
  - `atlassian.py get` — raw GET to any Atlassian URL.
  - `atlassian.py upload` — update Confluence page content.
  - `atlassian.py token` — manage tokens (list/set/remove/test).
- **Input**: CLI arguments. Domains from `ATLASSIAN_CONFLUENCE` and `ATLASSIAN_JIRA` environment variables.
- **Output**: stdout (text or JSON). Tokens in `data/tokens.json`. Page cache in `data/pages/`. Index at `data/page-index.json`.

## Behavior

### page

Fetch a Confluence page, extract metadata, cache content.

```bash
python3 atlassian.py page <pageId>
```

Process:
1. GET `/rest/api/content/<pageId>?expand=body.storage,version`.
2. Extract title, version number, author (`version.by.displayName`), updated time (`version.when`).
3. Convert Storage HTML to plain text.
4. Write text to `data/pages/<pageId>.txt`.
5. Update `data/page-index.json` with `{title, version, author, updated}`.
6. Print metadata header and text content to stdout.

Output: metadata header (`title`, `version`, `author`, `updated`) followed by plain text content.

### lookup

Search the local page index by keyword.

```bash
python3 atlassian.py lookup <keyword>
```

Process: all words in keyword must match the title (case-insensitive).

Output: `pageId  title` per match, one per line.

### search

Search Confluence via CQL.

```bash
python3 atlassian.py search <query> [--space SPACEKEY]
```

Process: query Confluence CQL, return up to 10 results, update page index with titles.

Output: `pageId  title` per result, one per line.

### issue

Fetch a Jira issue.

```bash
python3 atlassian.py issue <issueKey>
```

Output: JSON with summary, status, description, assignee, priority, labels.

### jql

Search Jira via JQL.

```bash
python3 atlassian.py jql <query>
```

Output: up to 20 results as JSON.

### add-comment

Add a comment to a Jira issue.

```bash
python3 atlassian.py add-comment <issueKey> "<body>"
```

Output: confirmation message with comment ID.

### get

Raw GET request to any Atlassian URL. Domain extracted from URL for token lookup.

```bash
python3 atlassian.py get <url>
```

Output: raw response body.

### upload

Update a Confluence page with Storage format HTML.

```bash
python3 atlassian.py upload <pageId> <file.storage.html>
```

Process: read current version, increment by 1, PUT new content.

Output: confirmation message with new version number.

### token

Manage Bearer tokens per domain.

```bash
python3 atlassian.py token list
python3 atlassian.py token set <domain> <pat>
python3 atlassian.py token remove <domain>
python3 atlassian.py token test <domain>
```

Output: `list` prints configured domains. `set`/`remove` print confirmation. `test` prints OK, EXPIRED, or FAILED.
