"""Tests for the comment thread backend (Phase 5)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import comments  # noqa: E402
from memex_docsite import config as cfg_mod  # noqa: E402


def test_add_comment_creates_jsonl_file(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    rec = comments.add_comment(
        cfg, "architecture/concept", body="Nice page.", author="alice"
    )
    assert rec["id"]
    assert rec["body"] == "Nice page."
    assert rec["author"] == "alice"
    assert rec["status"] == "active"
    assert rec["replies_to"] is None

    path = comments.comments_path(cfg, "architecture/concept")
    assert path.is_file()
    content = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1


def test_path_flattens_slashes(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    path = comments.comments_path(cfg, "a/b/c")
    assert path.name == "a__b__c.jsonl"


def test_add_comment_rejects_empty_body(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(comments.CommentError, match="body is required"):
        comments.add_comment(cfg, "page", body="   ", author="alice")


def test_add_comment_rejects_path_traversal(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(comments.CommentError):
        comments.add_comment(cfg, "../../etc", body="x", author="alice")


def test_replies_require_existing_parent(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(comments.CommentError, match="parent comment not found"):
        comments.add_comment(
            cfg, "page", body="reply", author="alice", replies_to="ghost"
        )


def test_list_orders_by_created(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    a = comments.add_comment(cfg, "page", body="first", author="alice")
    b = comments.add_comment(cfg, "page", body="second", author="bob")
    items = comments.list_comments(
        cfg, "page", viewer_name="anon", is_authenticated=False
    )
    assert [i["id"] for i in items] == [a["id"], b["id"]]


def test_list_visibility_filtering(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    comments.add_comment(cfg, "page", body="public-c", author="alice", visibility="public")
    comments.add_comment(cfg, "page", body="group-c", author="alice", visibility="group")
    comments.add_comment(cfg, "page", body="private-c", author="alice", visibility="private")

    anon = comments.list_comments(cfg, "page", viewer_name="anon", is_authenticated=False)
    assert {c["body"] for c in anon} == {"public-c"}

    bob = comments.list_comments(cfg, "page", viewer_name="bob", is_authenticated=True)
    assert {c["body"] for c in bob} == {"public-c", "group-c"}

    alice = comments.list_comments(cfg, "page", viewer_name="alice", is_authenticated=True)
    assert {c["body"] for c in alice} == {"public-c", "group-c", "private-c"}


def test_threading_with_replies(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    parent = comments.add_comment(cfg, "page", body="parent", author="alice")
    comments.add_comment(
        cfg, "page", body="reply", author="bob", replies_to=parent["id"]
    )
    items = comments.list_comments(
        cfg, "page", viewer_name="bob", is_authenticated=True
    )
    assert {(c["body"], c["replies_to"]) for c in items} == {
        ("parent", None),
        ("reply", parent["id"]),
    }


def test_update_comment_author_only(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    rec = comments.add_comment(cfg, "page", body="orig", author="alice")
    updated = comments.update_comment(
        cfg, "page", rec["id"], body="revised", visibility=None, author="alice"
    )
    assert updated["body"] == "revised"
    with pytest.raises(comments.CommentError, match="own comments"):
        comments.update_comment(
            cfg, "page", rec["id"], body="hijack", visibility=None, author="bob"
        )


def test_delete_comment_soft_deletes(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    rec = comments.add_comment(cfg, "page", body="delete me", author="alice")
    comments.delete_comment(cfg, "page", rec["id"], author="alice")
    items = comments.list_comments(
        cfg, "page", viewer_name="alice", is_authenticated=True
    )
    deleted = next(c for c in items if c["id"] == rec["id"])
    assert deleted["status"] == "deleted"
    assert deleted["body"] == "_(deleted)_"


def test_invalid_visibility(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(comments.CommentError, match="visibility must be one of"):
        comments.add_comment(
            cfg, "page", body="x", author="alice", visibility="bogus"  # type: ignore[arg-type]
        )


def test_list_recent_across_pages(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    comments.add_comment(cfg, "page-a", body="A", author="alice")
    comments.add_comment(cfg, "page-b", body="B", author="bob")
    comments.add_comment(cfg, "deeper/path", body="C", author="alice")
    recent = comments.list_recent_across_pages(
        cfg, viewer_name="anon", is_authenticated=False, limit=10
    )
    pages = [r["page"] for r in recent]
    bodies = [r["body"] for r in recent]
    assert set(pages) == {"page-a", "page-b", "deeper/path"}
    assert set(bodies) == {"A", "B", "C"}
    # Each record gets a `url` for the originating page.
    assert all(r["url"].startswith("/") for r in recent)


def test_list_recent_respects_visibility(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    comments.add_comment(cfg, "p1", body="public", author="alice", visibility="public")
    comments.add_comment(cfg, "p2", body="private", author="alice", visibility="private")
    public_only = comments.list_recent_across_pages(
        cfg, viewer_name="bob", is_authenticated=False, limit=10
    )
    assert {r["body"] for r in public_only} == {"public"}


def test_list_recent_orders_by_created_desc(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    # Pre-seed the JSONL with explicit out-of-order timestamps so the sort
    # behaviour is deterministic (the live `_now_iso()` only has 1-second
    # resolution).
    path = comments.comments_path(cfg, "p")
    path.parent.mkdir(parents=True, exist_ok=True)
    earlier = (
        '{"id":"older","author":"alice","visibility":"public","created":'
        '"2026-04-26T15:30:00Z","updated":null,"body":"first","replies_to":null,'
        '"status":"active"}\n'
    )
    later = (
        '{"id":"newer","author":"alice","visibility":"public","created":'
        '"2026-04-26T16:30:00Z","updated":null,"body":"second","replies_to":null,'
        '"status":"active"}\n'
    )
    path.write_text(earlier + later, encoding="utf-8")

    recent = comments.list_recent_across_pages(
        cfg, viewer_name="alice", is_authenticated=True
    )
    assert recent[0]["id"] == "newer"
    assert recent[1]["id"] == "older"


def test_corrupt_lines_are_skipped(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    comments.add_comment(cfg, "page", body="ok", author="alice")
    path = comments.comments_path(cfg, "page")
    # Append a line of garbage and a line that's valid JSON but not a dict.
    with path.open("a", encoding="utf-8") as f:
        f.write("not json at all\n")
        f.write("[1,2,3]\n")
    items = comments.list_comments(
        cfg, "page", viewer_name="alice", is_authenticated=True
    )
    assert len(items) == 1
