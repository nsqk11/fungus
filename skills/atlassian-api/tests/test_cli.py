"""Smoke tests for the CLI — argparse wiring and exit codes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import auth
import cli
import jira as jira_mod


# Reuse FakeConfluence / FakeJira from sibling test files via import.
from test_confluence import FakeConfluence
from test_jira import FakeJira


@pytest.fixture
def sample_raw() -> dict[str, Any]:
    return {
        "key": "PROJ-1",
        "fields": {
            "summary": "Hello",
            "status": {"name": "Open"},
            "issuetype": {"name": "Task"},
            "priority": {"name": "Low"},
            "assignee": {"displayName": "A"},
            "reporter": {"displayName": "B"},
            "created": "2026-04-20T00:00:00.000+0000",
            "updated": "2026-04-28T00:00:00.000+0000",
            "description": "desc",
            "comment": {"comments": []},
        },
    }


def test_token_list_empty(tmp_db, capsys):
    assert cli.main(["token", "list"]) == 0
    assert "(no tokens stored)" in capsys.readouterr().out


def test_token_set_and_list(tmp_db, capsys):
    assert cli.main(["token", "set", "example.com", "p"]) == 0
    assert cli.main(["token", "list"]) == 0
    out = capsys.readouterr().out
    assert "example.com" in out
    assert "unknown" in out


def test_token_remove_success(tmp_db, capsys):
    cli.main(["token", "set", "example.com", "p"])
    capsys.readouterr()
    assert cli.main(["token", "remove", "example.com"]) == 0


def test_token_remove_missing(tmp_db, capsys):
    assert cli.main(["token", "remove", "no.such.example.com"]) == 1


def test_fetch_unknown_url(tmp_db, capsys):
    rc = cli.main(["fetch", "https://example.com/random"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Unrecognised" in err


def test_fetch_confluence_url(tmp_db, monkeypatch, capsys):
    fc = FakeConfluence()
    fc.add_page("42", "My Page", "DEV", version=1, body_html="<p>Hello</p>")
    monkeypatch.setattr(auth, "get_confluence", lambda d: fc)

    rc = cli.main([
        "fetch",
        "https://example.com/spaces/DEV/pages/42/My-Page",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "title: My Page" in out
    assert "Hello" in out


def test_fetch_jira_url(tmp_db, monkeypatch, capsys, sample_raw):
    monkeypatch.setattr(auth, "get_jira", lambda d: FakeJira(sample_raw))

    rc = cli.main(["fetch", "https://example.com/browse/PROJ-1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PROJ-1: Hello" in out


def test_fetch_jira_html_format_refused(tmp_db, capsys):
    rc = cli.main(["fetch", "https://example.com/browse/PROJ-1", "--format", "html"])
    assert rc == 1
    assert "not supported" in capsys.readouterr().err


def test_page_json_format(tmp_db, monkeypatch, capsys):
    fc = FakeConfluence()
    fc.add_page("1", "T", "DEV", version=1, body_html="<p>x</p>")
    monkeypatch.setattr(auth, "get_confluence", lambda d: fc)

    rc = cli.main(["page", "example.com", "1", "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    import json as _json
    payload = _json.loads(out)
    assert payload["title"] == "T"


def test_issue_json_format(tmp_db, monkeypatch, capsys, sample_raw):
    monkeypatch.setattr(auth, "get_jira", lambda d: FakeJira(sample_raw))

    rc = cli.main(["issue", "example.com", "PROJ-1", "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    import json as _json
    payload = _json.loads(out)
    assert payload["key"] == "PROJ-1"


def test_search_no_results(tmp_db, capsys):
    rc = cli.main(["search", "nothing"])
    assert rc == 0
    assert "(no results)" in capsys.readouterr().out


def test_sync_prints_count(tmp_db, monkeypatch, capsys):
    fc = FakeConfluence()
    fc.add_page("1", "A", "DEV", version=1, body_html="<p>x</p>")
    monkeypatch.setattr(auth, "get_confluence", lambda d: fc)

    rc = cli.main(["sync", "example.com", "DEV"])
    assert rc == 0
    assert "Synced 1 page" in capsys.readouterr().out
