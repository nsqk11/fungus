"""Tests for confluence.py — caching, search, sync with a fake client."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import auth
import confluence


class FakeConfluence:
    """In-memory stand-in for atlassian.Confluence."""

    def __init__(self) -> None:
        self.pages: dict[str, dict[str, Any]] = {}
        self.spaces: dict[str, list[str]] = {}
        self.get_page_calls: int = 0

    def add_page(
        self,
        page_id: str,
        title: str,
        space: str,
        version: int,
        body_html: str,
        updated: str = "2026-04-28T00:00:00Z",
        author: str = "Alice",
    ) -> None:
        self.pages[page_id] = {
            "id": page_id,
            "title": title,
            "space": {"key": space},
            "version": {
                "number": version,
                "when": updated,
                "by": {"displayName": author},
            },
            "body": {"storage": {"value": body_html}},
        }
        self.spaces.setdefault(space, []).append(page_id)

    def get_page_by_id(self, page_id: str, expand: str = "") -> dict[str, Any]:
        self.get_page_calls += 1
        page = self.pages[page_id]
        # Mimic "meta-only" vs "full" expansions.
        if "body.storage" in expand:
            return page
        trimmed = {k: v for k, v in page.items() if k != "body"}
        return trimmed

    def get_all_pages_from_space(
        self,
        space: str,
        start: int = 0,
        limit: int = 100,
        expand: str = "",  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        ids = self.spaces.get(space, [])
        slice_ = ids[start : start + limit]
        return [self.pages[i] for i in slice_]


@pytest.fixture
def fake(monkeypatch, tmp_db: Path) -> FakeConfluence:
    fc = FakeConfluence()
    monkeypatch.setattr(auth, "get_confluence", lambda domain: fc)
    return fc


def test_fetch_page_miss_then_hit(fake: FakeConfluence):
    fake.add_page("42", "Hello", "DEV", version=1, body_html="<p>Hi</p>")

    first = confluence.fetch_page("example.com", "42")
    assert first.title == "Hello"
    assert first.version == 1
    assert "Hi" in first.body_text
    # First fetch: one meta call + one full call = 2
    assert fake.get_page_calls == 2

    # Second fetch with the same version: only the meta call, no refetch
    fake.get_page_calls = 0
    second = confluence.fetch_page("example.com", "42")
    assert second.body_text == first.body_text
    assert fake.get_page_calls == 1


def test_fetch_page_refresh_always_full(fake: FakeConfluence):
    fake.add_page("42", "Hello", "DEV", version=1, body_html="<p>Hi</p>")
    confluence.fetch_page("example.com", "42")  # prime cache
    fake.get_page_calls = 0

    confluence.fetch_page("example.com", "42", refresh=True)
    # --refresh skips the meta call and goes straight to full body
    assert fake.get_page_calls == 1


def test_fetch_page_updated_version_refetches(fake: FakeConfluence):
    fake.add_page("42", "V1", "DEV", version=1, body_html="<p>one</p>")
    confluence.fetch_page("example.com", "42")

    fake.add_page("42", "V2", "DEV", version=2, body_html="<p>two</p>")
    result = confluence.fetch_page("example.com", "42")
    assert result.version == 2
    assert "two" in result.body_text


def test_search_matches_title_and_body(fake: FakeConfluence):
    fake.add_page(
        "1", "Deployment Guide", "DEV", version=1, body_html="<p>kubernetes</p>"
    )
    fake.add_page(
        "2", "Travel Notes", "PERSONAL", version=1, body_html="<p>Paris</p>"
    )
    confluence.fetch_page("example.com", "1")
    confluence.fetch_page("example.com", "2")

    hits = [p.page_id for p in confluence.search_pages("kubernetes")]
    assert hits == ["1"]
    hits = [p.page_id for p in confluence.search_pages("Travel")]
    assert hits == ["2"]


def test_search_title_only(fake: FakeConfluence):
    fake.add_page(
        "1", "Deployment", "DEV", version=1, body_html="<p>kubernetes</p>"
    )
    confluence.fetch_page("example.com", "1")
    # "kubernetes" is only in body; title-only search should miss.
    assert confluence.search_pages("kubernetes", title_only=True) == []
    # The title is found.
    hits = confluence.search_pages("Deployment", title_only=True)
    assert len(hits) == 1


def test_search_domain_scope(fake: FakeConfluence, monkeypatch):
    fake.add_page("1", "Foo", "DEV", version=1, body_html="<p>a</p>")
    confluence.fetch_page("example.com", "1")

    # Create a second fake for another domain.
    other = FakeConfluence()
    other.add_page("2", "Foo", "DEV", version=1, body_html="<p>b</p>")
    monkeypatch.setattr(
        auth, "get_confluence",
        lambda d: other if d == "other.com" else fake,
    )
    confluence.fetch_page("other.com", "2")

    # All domains:
    assert len(confluence.search_pages("Foo")) == 2
    # Scoped to example.com only:
    scoped = confluence.search_pages("Foo", domain="example.com")
    assert len(scoped) == 1
    assert scoped[0].domain == "example.com"


def test_sync_space_populates_titles(fake: FakeConfluence):
    fake.add_page("1", "Alpha", "DEV", version=1, body_html="<p>a</p>")
    fake.add_page("2", "Beta", "DEV", version=1, body_html="<p>b</p>")
    fake.add_page("3", "Gamma", "DEV", version=1, body_html="<p>c</p>")

    count = confluence.sync_space("example.com", "DEV")
    assert count == 3
    hits = [p.title for p in confluence.search_pages("Alpha", title_only=True)]
    assert "Alpha" in hits


def test_sync_space_skips_already_cached(fake: FakeConfluence):
    fake.add_page("1", "Alpha", "DEV", version=1, body_html="<p>a</p>")
    confluence.fetch_page("example.com", "1")  # already has body
    fake.add_page("2", "Beta", "DEV", version=1, body_html="<p>b</p>")
    count = confluence.sync_space("example.com", "DEV")
    # Page 1 is skipped (body present); page 2 is inserted.
    assert count == 1
