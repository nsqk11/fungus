"""Tests for _store.py."""
from __future__ import annotations

import json

import pytest

import _store


def test_create_and_load(workbench_dir):
    wb = _store.create("proj-1", "First project", "feature")
    assert wb["id"] == "proj-1"
    assert wb["name"] == "First project"
    assert wb["type"] == "feature"
    assert wb["status"] == "active"
    assert wb["createdAt"]
    assert wb["updatedAt"]

    loaded = _store.load("proj-1")
    assert loaded == wb


def test_create_duplicate_errors(workbench_dir):
    _store.create("proj-1", "name")
    with pytest.raises(_store.StoreError):
        _store.create("proj-1", "another")


def test_create_invalid_id(workbench_dir):
    for bad in ["", "with space", "has/slash", "up..", "x" * 65]:
        with pytest.raises(_store.StoreError):
            _store.create(bad, "name")


def test_save_updates_updatedAt(workbench_dir):
    wb = _store.create("proj", "name")
    first = wb["updatedAt"]
    # Mutate + save
    wb["notes"].append({"topic": "t", "content": "c"})
    _store.save(wb)
    reloaded = _store.load("proj")
    assert reloaded["updatedAt"] >= first
    assert reloaded["createdAt"] == wb["createdAt"]


def test_atomic_write_no_tmp_leftover(workbench_dir):
    _store.create("proj", "name")
    tmps = list(workbench_dir.glob("*.tmp"))
    assert tmps == []


def test_resolve_id_exact(workbench_dir):
    _store.create("proj-1", "one")
    _store.create("proj-2", "two")
    assert _store.resolve_id("proj-1") == "proj-1"


def test_resolve_id_unique_prefix(workbench_dir):
    _store.create("alpha", "a")
    _store.create("beta", "b")
    assert _store.resolve_id("alp") == "alpha"


def test_resolve_id_ambiguous(workbench_dir):
    _store.create("proj-1", "one")
    _store.create("proj-2", "two")
    with pytest.raises(_store.StoreError) as exc:
        _store.resolve_id("proj")
    assert "ambiguous" in str(exc.value)


def test_resolve_id_not_found(workbench_dir):
    with pytest.raises(_store.StoreError):
        _store.resolve_id("nope")


def test_resolve_id_exact_flag(workbench_dir):
    _store.create("alpha", "a")
    with pytest.raises(_store.StoreError):
        _store.resolve_id("alp", exact=True)


def test_list_ids_sorted(workbench_dir):
    for wb_id in ["gamma", "alpha", "beta"]:
        _store.create(wb_id, wb_id)
    assert _store.list_ids() == ["alpha", "beta", "gamma"]


def test_data_dir_env_override(workbench_dir):
    # Fixture sets PROJECT_WORKBENCH_DIR; confirm data_dir returns it.
    assert _store.data_dir() == workbench_dir


def test_json_round_trip_preserves_unicode(workbench_dir):
    wb = _store.create("unicode", "名字")
    wb["notes"].append({"topic": "中文", "content": "内容包含 emoji 🚀"})
    _store.save(wb)
    raw = (workbench_dir / "unicode.json").read_text(encoding="utf-8")
    # ensure_ascii=False means unicode is written directly, not escaped.
    assert "中文" in raw
    assert "\\u" not in raw or raw.count("\\u") == 0
    reloaded = _store.load("unicode")
    assert reloaded["notes"][0]["content"] == "内容包含 emoji 🚀"


def test_load_missing_file_errors(workbench_dir):
    with pytest.raises(_store.StoreError):
        _store.load("nope")


def test_load_corrupted_json_errors(workbench_dir):
    (workbench_dir / "bad.json").write_text("{not valid", encoding="utf-8")
    with pytest.raises(_store.StoreError):
        _store.load("bad")


def test_saved_file_is_formatted_json(workbench_dir):
    _store.create("proj", "name")
    raw = (workbench_dir / "proj.json").read_text(encoding="utf-8")
    # Indented with 2 spaces, trailing newline.
    assert raw.startswith("{\n  ")
    assert raw.endswith("\n")
    # Round-trip safe.
    json.loads(raw)
