"""Tests for cli.py — invoke main() with argv lists and assert on
captured stdout and the on-disk JSON.
"""
from __future__ import annotations

import json

import pytest

import _store
import cli


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    """Invoke cli.main with argv and return (code, stdout, stderr)."""
    try:
        code = cli.main(list(argv))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_init_creates_file(workbench_dir, capsys):
    code, out, _ = _run(capsys, "init", "proj", "--name", "First", "--type", "feature")
    assert code == 0
    assert "created proj" in out
    path = workbench_dir / "proj.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == "proj"
    assert data["type"] == "feature"
    assert data["reviews"] == []  # new key name
    assert "review" not in data  # old singular key is gone


def test_init_duplicate_exits_nonzero(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "a")
    code, _, err = _run(capsys, "init", "proj", "--name", "b")
    assert code != 0
    assert "already exists" in err


def test_query_prints_whole_workbench(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    code, out, _ = _run(capsys, "query", "proj")
    assert code == 0
    data = json.loads(out)
    assert data["id"] == "proj"


def test_query_field_path(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(capsys, "milestone", "add", "proj", "--name", "M1", "--note", "blocker")
    code, out, _ = _run(capsys, "query", "proj", "--field", "milestones.0.note")
    assert code == 0
    assert json.loads(out) == "blocker"


def test_query_field_missing_errors(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    code, _, err = _run(capsys, "query", "proj", "--field", "doesnt.exist")
    assert code != 0
    assert "not found" in err


def test_log_appends_entry(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(capsys, "log", "proj", "--summary", "first change", "--ref", "abc1234")
    wb = _store.load("proj")
    assert len(wb["changeLog"]) == 1
    assert wb["changeLog"][0]["summary"] == "first change"
    assert wb["changeLog"][0]["ref"] == "abc1234"
    assert wb["changeLog"][0]["date"]  # auto-filled


def test_review_add_and_done(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(
        capsys,
        "review", "add", "proj",
        "--location", "Section 3",
        "--comment", "needs rewording",
        "--by", "Alex",
    )
    wb = _store.load("proj")
    assert wb["reviews"][0]["id"] == 1
    assert wb["reviews"][0]["done"] is False

    _run(
        capsys,
        "review", "done", "proj",
        "--review-id", "1",
        "--response", "rewritten",
    )
    wb = _store.load("proj")
    assert wb["reviews"][0]["done"] is True
    assert wb["reviews"][0]["response"] == "rewritten"


def test_review_done_missing_id_errors(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    code, _, err = _run(capsys, "review", "done", "proj", "--review-id", "99")
    assert code != 0
    assert "not found" in err


def test_milestone_lifecycle(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(capsys, "milestone", "add", "proj", "--name", "Kickoff", "--target", "WK1")
    _run(capsys, "milestone", "update", "proj", "--name", "Kickoff", "--target", "WK2")
    _run(capsys, "milestone", "done", "proj", "--name", "Kickoff", "--note", "ok")
    wb = _store.load("proj")
    assert wb["milestones"][0]["target"] == "WK2"
    assert wb["milestones"][0]["done"] is True
    assert wb["milestones"][0]["note"] == "ok"


def test_note_adds_entry(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(
        capsys,
        "note", "proj",
        "--topic", "Why B over A",
        "--content", "A violates invariant Z",
    )
    wb = _store.load("proj")
    assert wb["notes"][0]["topic"] == "Why B over A"


def test_status_lists_pending(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(capsys, "milestone", "add", "proj", "--name", "M1", "--target", "WK1")
    _run(capsys, "milestone", "add", "proj", "--name", "M2")
    _run(capsys, "milestone", "done", "proj", "--name", "M2")
    code, out, _ = _run(capsys, "status", "proj")
    assert code == 0
    assert "Milestones pending: 1" in out
    assert "M1" in out
    assert "M2" not in out  # done milestones are hidden


def test_list_and_filter(workbench_dir, capsys):
    _run(capsys, "init", "a", "--name", "A")
    _run(capsys, "init", "b", "--name", "B")
    _run(capsys, "archive", "b")

    code, out, _ = _run(capsys, "list")
    assert code == 0
    assert "a" in out and "b" in out

    code, out, _ = _run(capsys, "list", "--status", "active")
    assert "a" in out
    assert "archived" not in out


def test_remind_excludes_paused_and_done(workbench_dir, capsys):
    _run(capsys, "init", "a", "--name", "A")
    _run(capsys, "milestone", "add", "a", "--name", "open")
    _run(capsys, "init", "b", "--name", "B")
    _run(capsys, "milestone", "add", "b", "--name", "also-open")
    _run(capsys, "done", "b")  # 'b' no longer active

    code, out, _ = _run(capsys, "remind")
    assert code == 0
    assert "[a]" in out
    assert "[b]" not in out


def test_remind_empty(workbench_dir, capsys):
    _run(capsys, "init", "a", "--name", "A")
    code, out, _ = _run(capsys, "remind")
    assert code == 0
    assert "No pending items" in out


def test_archive_and_done(workbench_dir, capsys):
    _run(capsys, "init", "proj", "--name", "X")
    _run(capsys, "archive", "proj")
    assert _store.load("proj")["status"] == "archived"
    _run(capsys, "done", "proj")
    assert _store.load("proj")["status"] == "done"


def test_prefix_match_resolves(workbench_dir, capsys):
    _run(capsys, "init", "my-long-id", "--name", "X")
    code, out, _ = _run(capsys, "query", "my-lo")
    assert code == 0
    assert json.loads(out)["id"] == "my-long-id"


def test_prefix_ambiguous_errors(workbench_dir, capsys):
    _run(capsys, "init", "proj-a", "--name", "A")
    _run(capsys, "init", "proj-b", "--name", "B")
    code, _, err = _run(capsys, "query", "proj")
    assert code != 0
    assert "ambiguous" in err
