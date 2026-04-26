"""Tests for the file-write helpers (Phase 3)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import config as cfg_mod  # noqa: E402
from memex_docsite import frontmatter, submissions  # noqa: E402


def test_slugify_basics():
    assert submissions.slugify("Hello, World!") == "hello-world"
    assert submissions.slugify("  Spaced  Out  ") == "spaced-out"
    assert submissions.slugify("Mixed-Case AND Numbers 123") == "mixed-case-and-numbers-123"


def test_slugify_falls_back_for_empty():
    out = submissions.slugify("")
    assert out.startswith("untitled-")


def test_unique_slug_appends_counters(tmp_path: Path):
    (tmp_path / "foo.md").write_text("x", encoding="utf-8")
    (tmp_path / "foo-2.md").write_text("x", encoding="utf-8")
    assert submissions.unique_slug(tmp_path, "foo") == "foo-3"
    assert submissions.unique_slug(tmp_path, "bar") == "bar"


def test_submit_open_question_writes_valid_file(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    result = submissions.submit_open_question(
        cfg,
        title="Where does episodic memory live?",
        body="Looking for the canonical doc.",
        author="alice",
        owner="alice",
    )
    assert result.path.is_file()
    content = result.path.read_text(encoding="utf-8")
    fm, body = frontmatter.split(content)
    assert fm["type"] == "open-question"
    assert fm["title"] == "Where does episodic memory live?"
    assert fm["author"] == "alice"
    assert fm["owner"] == "alice"
    assert fm["status"] == "draft"
    assert fm["created"] == fm["updated"]
    assert "Looking for the canonical doc." in body


def test_submit_open_question_validates_against_required_fields(
    research_wiki_project: Path,
):
    """If a profile demands a frontmatter field the docsite doesn't supply,
    submission should fail rather than write a broken file."""
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw.setdefault("frontmatter", {}).setdefault("required", []).append("definitely_required")
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    with pytest.raises(ValueError, match="frontmatter validation failed"):
        submissions.submit_open_question(
            cfg, title="x", body="y", author="z"
        )


def test_resolve_open_question_moves_file(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    result = submissions.submit_open_question(
        cfg, title="Q", body="B", author="alice"
    )
    assert result.path.is_file()
    submissions.resolve_open_question(cfg, result.slug, resolver="bob")
    assert not result.path.is_file()
    resolved = (
        cfg.wiki_root / submissions.OPEN_QUESTIONS_DIR / submissions.RESOLVED_DIR / f"{result.slug}.md"
    )
    assert resolved.is_file()
    fm, _ = frontmatter.split(resolved.read_text(encoding="utf-8"))
    assert fm["status"] == "resolved"
    assert fm["resolved_by"] == "bob"


def test_submit_rule_writes_valid_file(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    result = submissions.submit_rule(
        cfg,
        title="Always cite sources",
        body="Cite at least one provenance hash per claim.",
        author="alice",
        scope="wiki/syntheses/*",
    )
    assert result.path.is_file()
    fm, body = frontmatter.split(result.path.read_text(encoding="utf-8"))
    assert fm["type"] == "rule"
    assert fm["scope"] == "wiki/syntheses/*"
    assert "Cite at least one provenance hash" in body


def test_list_open_questions_buckets_active_and_resolved(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    a = submissions.submit_open_question(cfg, title="A", body="aa", author="x")
    b = submissions.submit_open_question(cfg, title="B", body="bb", author="x")
    submissions.resolve_open_question(cfg, b.slug, resolver="y")

    items = submissions.list_open_questions(cfg)
    active_slugs = {i["slug"] for i in items if not i["resolved"]}
    resolved_slugs = {i["slug"] for i in items if i["resolved"]}
    assert a.slug in active_slugs
    assert b.slug in resolved_slugs


def test_list_rules_returns_summaries(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    submissions.submit_rule(cfg, title="One", body="b1", author="x")
    submissions.submit_rule(cfg, title="Two", body="b2", author="x")
    rules = submissions.list_rules(cfg)
    titles = {r["title"] for r in rules}
    assert {"One", "Two"} <= titles
    assert all(r.get("url") for r in rules)


def test_inline_status_resolved_counts_as_resolved(research_wiki_project: Path):
    """A page with `status: resolved` in its frontmatter must show up in the
    resolved bucket even though it still lives in `.open-questions/` (not
    yet moved to `.resolved/`). This is the bug T2 fixes — the previous
    implementation hard-coded resolution from folder location only."""
    cfg = cfg_mod.load(start=research_wiki_project)
    folder = cfg.memex_root / submissions.OPEN_QUESTIONS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    inline = folder / "inline-resolved.md"
    inline.write_text(
        "---\n"
        "title: Already answered\n"
        "slug: inline-resolved\n"
        "type: open-question\n"
        "status: resolved\n"
        "resolved-on: '2026-04-20'\n"
        "resolved-by: alice\n"
        "created: '2026-04-01T00:00:00Z'\n"
        "updated: '2026-04-20T00:00:00Z'\n"
        "owner: alice\n"
        "---\nbody\n",
        encoding="utf-8",
    )
    items = submissions.list_open_questions(cfg)
    inline_item = next(i for i in items if i["slug"] == "inline-resolved")
    assert inline_item["resolved"] is True
    assert inline_item["status"] == "resolved"
    assert inline_item["resolved_on"] == "2026-04-20"
    assert inline_item["resolved_by"] == "alice"


def test_is_resolved_helper_handles_both_conventions():
    """`is_resolved` must accept both the inline frontmatter convention and
    the `.resolved/` folder convention, and return False otherwise."""
    p = Path(".open-questions/foo.md")
    assert submissions.is_resolved(p, {"status": "resolved"}) is True
    assert submissions.is_resolved(p, {"status": "Resolved"}) is True
    assert submissions.is_resolved(p, {"status": "open"}) is False
    assert submissions.is_resolved(p, None) is False
    p2 = Path(".open-questions/.resolved/foo.md")
    assert submissions.is_resolved(p2, None) is True
    assert submissions.is_resolved(p2, {"status": "open"}) is True
