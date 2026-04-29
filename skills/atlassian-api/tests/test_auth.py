"""Tests for auth.py — token CRUD, test_token, client factories."""
from __future__ import annotations

import stat
from pathlib import Path

import pytest

import auth


def test_normalise_domain_bare():
    assert auth.normalise_domain("example.atlassian.net") == "example.atlassian.net"


def test_normalise_domain_url():
    assert (
        auth.normalise_domain("https://example.atlassian.net/wiki/spaces/DEV")
        == "example.atlassian.net"
    )


def test_normalise_domain_lowercases():
    assert auth.normalise_domain("Example.Atlassian.NET") == "example.atlassian.net"


def test_normalise_domain_empty_raises():
    with pytest.raises(ValueError):
        auth.normalise_domain("")


def test_set_get_roundtrip(tmp_db: Path):
    auth.set_token("example.atlassian.net", "s3cret")
    assert auth.get_token("example.atlassian.net") == "s3cret"


def test_set_updates_existing(tmp_db: Path):
    auth.set_token("example.atlassian.net", "one")
    auth.set_token("example.atlassian.net", "two")
    assert auth.get_token("example.atlassian.net") == "two"


def test_set_resets_status(tmp_db: Path):
    auth.set_token("example.atlassian.net", "p")
    auth._write_status("example.atlassian.net", "ok")
    row = [r for r in auth.list_tokens() if r.domain == "example.atlassian.net"][0]
    assert row.status == "ok"
    auth.set_token("example.atlassian.net", "p2")
    row = [r for r in auth.list_tokens() if r.domain == "example.atlassian.net"][0]
    assert row.status == "unknown"
    assert row.last_tested is None


def test_get_token_missing(tmp_db: Path):
    with pytest.raises(KeyError):
        auth.get_token("nope.atlassian.net")


def test_remove_token(tmp_db: Path):
    auth.set_token("example.atlassian.net", "p")
    assert auth.remove_token("example.atlassian.net") is True
    assert auth.remove_token("example.atlassian.net") is False


def test_list_tokens_sorted(tmp_db: Path):
    auth.set_token("b.example.net", "1")
    auth.set_token("a.example.net", "2")
    assert [r.domain for r in auth.list_tokens()] == [
        "a.example.net", "b.example.net"
    ]


def test_db_is_chmod_600(tmp_db: Path):
    auth.set_token("example.atlassian.net", "pat")
    mode = tmp_db.stat().st_mode & 0o777
    assert mode & (stat.S_IRWXG | stat.S_IRWXO) == 0


class _FakeConfluence:
    def __init__(self, behaviour: str):
        self.behaviour = behaviour

    def get_all_spaces(self, limit: int = 1):  # noqa: ARG002
        if self.behaviour == "ok":
            return {"results": []}
        if self.behaviour == "expired":
            raise RuntimeError("401 Unauthorized")
        raise RuntimeError("Connection refused")


def test_test_token_missing_raises(tmp_db: Path):
    with pytest.raises(KeyError):
        auth.test_token("nope.atlassian.net")


def test_test_token_ok(tmp_db: Path, monkeypatch):
    auth.set_token("example.atlassian.net", "p")
    monkeypatch.setattr(auth, "get_confluence", lambda d: _FakeConfluence("ok"))
    assert auth.test_token("example.atlassian.net") == "ok"
    row = [r for r in auth.list_tokens() if r.domain == "example.atlassian.net"][0]
    assert row.status == "ok"
    assert row.last_tested


def test_test_token_expired(tmp_db: Path, monkeypatch):
    auth.set_token("example.atlassian.net", "p")
    monkeypatch.setattr(
        auth, "get_confluence", lambda d: _FakeConfluence("expired")
    )
    assert auth.test_token("example.atlassian.net") == "expired"


def test_test_token_unknown(tmp_db: Path, monkeypatch):
    auth.set_token("example.atlassian.net", "p")
    monkeypatch.setattr(
        auth, "get_confluence", lambda d: _FakeConfluence("network")
    )
    assert auth.test_token("example.atlassian.net") == "unknown"
