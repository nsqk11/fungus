"""Tests for urls.py — classify standard Atlassian URL patterns."""
from __future__ import annotations

import urls


# --- Confluence ---


def test_confluence_spaces_pages_with_slug():
    r = urls.classify(
        "https://example.com/spaces/DEV/pages/12345/Page-Title"
    )
    assert r.kind == "confluence_page"
    assert r.host == "example.com"
    assert r.page_id == "12345"
    assert r.space == "DEV"


def test_confluence_spaces_pages_without_slug():
    r = urls.classify("https://example.com/spaces/DEV/pages/12345")
    assert r.kind == "confluence_page"
    assert r.page_id == "12345"
    assert r.space == "DEV"


def test_confluence_wiki_spaces_pages():
    r = urls.classify(
        "https://foo.atlassian.net/wiki/spaces/ENG/pages/67890/Something"
    )
    assert r.kind == "confluence_page"
    assert r.host == "foo.atlassian.net"
    assert r.page_id == "67890"
    assert r.space == "ENG"


def test_confluence_display():
    r = urls.classify(
        "https://example.com/display/DEV/Deployment+Guide"
    )
    assert r.kind == "confluence_page"
    assert r.space == "DEV"
    assert r.title == "Deployment Guide"


def test_confluence_wiki_display():
    r = urls.classify(
        "https://foo.atlassian.net/wiki/display/DEV/Hello+World"
    )
    assert r.kind == "confluence_page"
    assert r.space == "DEV"
    assert r.title == "Hello World"


def test_confluence_viewpage_action():
    r = urls.classify(
        "https://example.com/pages/viewpage.action?pageId=12345"
    )
    assert r.kind == "confluence_page"
    assert r.page_id == "12345"


def test_confluence_plain_pages_id():
    r = urls.classify("https://example.com/pages/12345")
    assert r.kind == "confluence_page"
    assert r.page_id == "12345"


def test_confluence_host_is_preserved_lowercase():
    r = urls.classify("https://EXAMPLE.Atlassian.NET/display/DEV/Foo")
    assert r.host == "example.atlassian.net"


# --- Jira ---


def test_jira_browse_simple():
    r = urls.classify("https://example.com/browse/PROJ-123")
    assert r.kind == "jira_issue"
    assert r.issue_key == "PROJ-123"


def test_jira_browse_with_trailing_query():
    r = urls.classify(
        "https://example.com/browse/PROJ-123?jql=assignee=x"
    )
    assert r.kind == "jira_issue"
    assert r.issue_key == "PROJ-123"


def test_jira_browse_complex_key():
    r = urls.classify("https://example.com/browse/PROJ_X-45")
    assert r.kind == "jira_issue"
    assert r.issue_key == "PROJ_X-45"


# --- Unknown ---


def test_unknown_path():
    r = urls.classify("https://example.com/some/other/path")
    assert r.kind == "unknown"


def test_unknown_empty():
    r = urls.classify("")
    assert r.kind == "unknown"


def test_unknown_jira_shape_lowercase():
    # /browse/xxx-123 is not valid; keys must be uppercase.
    r = urls.classify("https://example.com/browse/proj-123")
    assert r.kind == "unknown"
