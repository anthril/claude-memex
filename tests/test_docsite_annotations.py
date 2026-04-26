"""Tests for the annotation backend (Phase 4)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import annotations, frontmatter  # noqa: E402
from memex_docsite import config as cfg_mod

_SELECTOR = {
    "type": "TextQuoteSelector",
    "exact": "the hippocampus binds episodes",
    "prefix": "consolidation. ",
    "suffix": " for replay",
}
_POSITION = {"start": 100, "end": 130}


def test_create_annotation_writes_valid_file(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    result = annotations.create_annotation(
        cfg,
        "architecture/concept",
        body="This conflicts with the schema-lattice description.",
        selector=_SELECTOR,
        position=_POSITION,
        author="alice",
    )
    assert result.path.is_file()
    fm, body = frontmatter.split(result.path.read_text(encoding="utf-8"))
    assert fm["type"] == "annotation"
    assert fm["author"] == "alice"
    assert fm["page"] == "architecture/concept"
    assert fm["selector"]["exact"] == _SELECTOR["exact"]
    assert fm["position"]["start"] == 100
    assert "schema-lattice" in body


def test_create_annotation_rejects_missing_selector(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(annotations.AnnotationError):
        annotations.create_annotation(
            cfg, "page", body="x", selector=None, position=None, author="alice"
        )


def test_create_annotation_rejects_empty_body(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(annotations.AnnotationError):
        annotations.create_annotation(
            cfg, "page", body="   ", selector=_SELECTOR, position=None, author="alice"
        )


def test_create_annotation_rejects_path_traversal(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(annotations.AnnotationError):
        annotations.create_annotation(
            cfg, "../../etc/passwd", body="x",
            selector=_SELECTOR, position=None, author="alice"
        )


def test_list_annotations_filters_by_visibility(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    annotations.create_annotation(
        cfg, "page", body="public note", selector=_SELECTOR, position=None,
        author="alice", visibility="public",
    )
    annotations.create_annotation(
        cfg, "page", body="group note", selector=_SELECTOR, position=None,
        author="alice", visibility="group",
    )
    annotations.create_annotation(
        cfg, "page", body="private note", selector=_SELECTOR, position=None,
        author="alice", visibility="private",
    )

    # Anonymous viewer sees only public.
    anon = annotations.list_annotations(cfg, "page", viewer_name="anonymous", is_authenticated=False)
    assert {a["body"] for a in anon} == {"public note"}

    # Authenticated viewer (different user) sees public + group.
    bob = annotations.list_annotations(cfg, "page", viewer_name="bob", is_authenticated=True)
    assert {a["body"] for a in bob} == {"public note", "group note"}

    # Author sees all three.
    alice = annotations.list_annotations(cfg, "page", viewer_name="alice", is_authenticated=True)
    assert {a["body"] for a in alice} == {"public note", "group note", "private note"}


def test_update_annotation_author_only(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    result = annotations.create_annotation(
        cfg, "page", body="initial", selector=_SELECTOR, position=None, author="alice"
    )
    ann_id = result.record["id"]

    # Author can update.
    updated = annotations.update_annotation(
        cfg, "page", ann_id, body="revised", visibility="group",
        author="alice", is_authenticated=True,
    )
    assert updated.record["body"] == "revised"
    assert updated.record["visibility"] == "group"

    # Other users cannot.
    with pytest.raises(annotations.AnnotationError, match="own annotations"):
        annotations.update_annotation(
            cfg, "page", ann_id, body="hijacked", visibility=None,
            author="bob", is_authenticated=True,
        )


def test_delete_annotation_soft_deletes(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    result = annotations.create_annotation(
        cfg, "page", body="initial", selector=_SELECTOR, position=None, author="alice"
    )
    ann_id = result.record["id"]
    annotations.delete_annotation(
        cfg, "page", ann_id, author="alice", is_authenticated=True
    )
    # File still exists, but status is `deleted`.
    target = annotations.annotation_dir(cfg, "page") / f"{ann_id}.md"
    assert target.is_file()
    fm, _ = frontmatter.split(target.read_text(encoding="utf-8"))
    assert fm["status"] == "deleted"


def test_replies_link_to_parent(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    parent = annotations.create_annotation(
        cfg, "page", body="parent", selector=_SELECTOR, position=None, author="alice"
    )
    parent_id = parent.record["id"]
    reply = annotations.create_annotation(
        cfg, "page", body="reply", selector=_SELECTOR, position=None,
        author="bob", replies_to=parent_id,
    )
    assert reply.record["replies_to"] == parent_id
    # Listing returns both.
    items = annotations.list_annotations(cfg, "page", viewer_name="bob", is_authenticated=True)
    assert {a["body"] for a in items} == {"parent", "reply"}


def test_replies_to_nonexistent_parent_rejected(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(annotations.AnnotationError, match="parent annotation not found"):
        annotations.create_annotation(
            cfg, "page", body="x", selector=_SELECTOR, position=None,
            author="alice", replies_to="ghost-id",
        )


def test_create_with_invalid_visibility(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(annotations.AnnotationError, match="visibility must be one of"):
        annotations.create_annotation(
            cfg, "page", body="x", selector=_SELECTOR, position=None,
            author="alice", visibility="bogus",  # type: ignore[arg-type]
        )
