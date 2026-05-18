"""Jira issue fetch — always talks to the remote API, never caches.

Jira state changes often (status, comments, fields) and the benefit of
caching is outweighed by stale-read risk. This module is a thin convenience
wrapper: it authenticates via :mod:`auth` and formats the result. For any
writes, JQL searches, or bulk operations, the agent should construct its
own ``atlassian.Jira`` client (see ``references/client_setup.py``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import auth

__all__ = ["JiraIssue", "fetch_issue"]


@dataclass
class JiraIssue:
    """A minimal, display-friendly projection of a Jira issue."""

    domain: str
    issue_key: str
    summary: str
    status: str
    issuetype: str
    priority: str
    assignee: str
    reporter: str
    created_at: str
    updated_at: str
    description: str
    comments: list[dict[str, str]]
    raw: dict[str, Any]

    def as_text(self, max_comments: int | None = 10) -> str:
        """Render the issue as plain text.

        *max_comments* caps how many comments are shown (most recent first
        in the API response order). Pass ``None`` to print them all.
        """
        lines = [
            f"{self.issue_key}: {self.summary}",
            f"status: {self.status}",
            f"type: {self.issuetype}  priority: {self.priority}",
            f"assignee: {self.assignee}  reporter: {self.reporter}",
            f"created: {self.created_at}  updated: {self.updated_at}",
            "=" * 60,
            self.description or "(no description)",
        ]
        if self.comments:
            total = len(self.comments)
            if max_comments is None or total <= max_comments:
                shown = self.comments
                header = f"--- comments ({total}) ---"
            else:
                shown = self.comments[-max_comments:]
                header = (
                    f"--- comments (showing last {max_comments} of {total}; "
                    "pass --full for all) ---"
                )
            lines.append("")
            lines.append(header)
            for c in shown:
                lines.append(
                    f"[{c.get('created', '')}] {c.get('author', '')}:"
                )
                lines.append(c.get("body", ""))
        return "\n".join(lines)

    def as_json(self) -> str:
        return json.dumps(self.raw, indent=2, ensure_ascii=False)


def fetch_issue(
    domain: str,
    issue_key: str,
    *,
    client: Any | None = None,
) -> JiraIssue:
    """Fetch a Jira issue from the remote API. No caching.

    *client* is an optional ``atlassian.Jira`` instance; if omitted, one is
    constructed via :func:`auth.get_jira`.
    """
    domain = auth.normalise_domain(domain)
    if client is None:
        client = auth.get_jira(domain)
    raw = client.issue(issue_key)
    return _build_issue(domain, issue_key, raw)


def _build_issue(domain: str, issue_key: str, raw: dict[str, Any]) -> JiraIssue:
    fields = raw.get("fields", {}) or {}

    def _name(block: Any) -> str:
        if isinstance(block, dict):
            return block.get("name") or block.get("displayName") or ""
        return ""

    summary = fields.get("summary", "") or ""
    status = _name(fields.get("status"))
    issuetype = _name(fields.get("issuetype"))
    priority = _name(fields.get("priority"))
    assignee = _name(fields.get("assignee"))
    reporter = _name(fields.get("reporter"))
    created_at = fields.get("created", "") or ""
    updated_at = fields.get("updated", "") or ""
    description = fields.get("description", "") or ""

    comment_block = fields.get("comment", {}) or {}
    raw_comments = comment_block.get("comments", []) or []
    comments: list[dict[str, str]] = []
    for c in raw_comments:
        author = (c.get("author") or {}).get("displayName", "") or ""
        comments.append({
            "id": str(c.get("id", "")),
            "author": author,
            "created": c.get("created", "") or "",
            "updated": c.get("updated", "") or "",
            "body": c.get("body", "") or "",
        })

    return JiraIssue(
        domain=domain,
        issue_key=issue_key,
        summary=summary,
        status=status,
        issuetype=issuetype,
        priority=priority,
        assignee=assignee,
        reporter=reporter,
        created_at=created_at,
        updated_at=updated_at,
        description=description,
        comments=comments,
        raw=raw,
    )
