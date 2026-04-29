"""Tests for jira.py — fetch_issue + JiraIssue rendering."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import auth
import jira


class FakeJira:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.calls = 0

    def issue(self, key: str) -> dict[str, Any]:  # noqa: ARG002
        self.calls += 1
        return self.data


@pytest.fixture
def sample_raw() -> dict[str, Any]:
    return {
        "key": "PROJ-123",
        "fields": {
            "summary": "Fix broken build",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "Alice"},
            "reporter": {"displayName": "Bob"},
            "created": "2026-04-20T10:00:00.000+0000",
            "updated": "2026-04-28T11:00:00.000+0000",
            "description": "Build fails on main.",
            "comment": {
                "comments": [
                    {
                        "id": "1",
                        "author": {"displayName": "Alice"},
                        "created": "2026-04-20T11:00:00.000+0000",
                        "updated": "2026-04-20T11:00:00.000+0000",
                        "body": "Looking into this.",
                    },
                    {
                        "id": "2",
                        "author": {"displayName": "Bob"},
                        "created": "2026-04-21T09:00:00.000+0000",
                        "updated": "2026-04-21T09:00:00.000+0000",
                        "body": "Root cause identified.",
                    },
                ],
            },
        },
    }


def test_fetch_issue_maps_fields(
    tmp_db: Path, monkeypatch, sample_raw: dict[str, Any]
):
    monkeypatch.setattr(auth, "get_jira", lambda d: FakeJira(sample_raw))
    issue = jira.fetch_issue("example.com", "PROJ-123")
    assert issue.summary == "Fix broken build"
    assert issue.status == "In Progress"
    assert issue.issuetype == "Bug"
    assert issue.priority == "High"
    assert issue.assignee == "Alice"
    assert issue.reporter == "Bob"
    assert len(issue.comments) == 2


def test_fetch_issue_injected_client(sample_raw: dict[str, Any]):
    fj = FakeJira(sample_raw)
    issue = jira.fetch_issue("example.com", "PROJ-123", client=fj)
    assert issue.summary.startswith("Fix")
    assert fj.calls == 1


def test_as_text_limits_comments(sample_raw: dict[str, Any]):
    # Bump up to 25 comments to test the last-10 default.
    comments = [
        {
            "id": str(i),
            "author": {"displayName": f"U{i}"},
            "created": f"2026-04-{(i % 28) + 1:02d}T00:00:00.000+0000",
            "updated": "2026-04-28T00:00:00.000+0000",
            "body": f"comment {i}",
        }
        for i in range(25)
    ]
    sample_raw["fields"]["comment"]["comments"] = comments
    issue = jira.fetch_issue("example.com", "PROJ-123", client=FakeJira(sample_raw))
    text_default = issue.as_text()
    assert "showing last 10 of 25" in text_default
    # The earliest comments should not appear in the default view.
    assert "comment 0" not in text_default
    assert "comment 24" in text_default

    text_full = issue.as_text(max_comments=None)
    assert "comment 0" in text_full
    assert "comment 24" in text_full


def test_as_text_small_comment_list_no_truncation_note(sample_raw):
    issue = jira.fetch_issue("example.com", "PROJ-123", client=FakeJira(sample_raw))
    text = issue.as_text()
    assert "comments (2)" in text
    assert "showing last" not in text


def test_as_json_roundtrip(sample_raw):
    issue = jira.fetch_issue("example.com", "PROJ-123", client=FakeJira(sample_raw))
    import json as _json
    payload = _json.loads(issue.as_json())
    assert payload["key"] == "PROJ-123"
    assert payload["fields"]["summary"] == "Fix broken build"


def test_missing_optional_fields_defaults_to_empty(tmp_db: Path, monkeypatch):
    raw = {"key": "X-1", "fields": {"summary": "S"}}
    monkeypatch.setattr(auth, "get_jira", lambda d: FakeJira(raw))
    issue = jira.fetch_issue("example.com", "X-1")
    assert issue.status == ""
    assert issue.priority == ""
    assert issue.assignee == ""
    assert issue.description == ""
    assert issue.comments == []
