"""Tests for `memex_docsite.sections` (T1 — profile-driven sections nav)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import config as cfg_mod  # noqa: E402
from memex_docsite import sections as sections_mod  # noqa: E402
from memex_docsite.graph import Graph, Node  # noqa: E402


def test_slugify_label_basic():
    assert sections_mod.slugify_label("Open Questions") == "open-questions"
    assert sections_mod.slugify_label("Recent Activity") == "recent-activity"
    assert sections_mod.slugify_label("Plot Threads!") == "plot-threads"


def test_label_to_type_value_explicit_overrides():
    enum = ["entity", "concept", "summary", "analysis", "synthesis", "open-question"]
    assert sections_mod._label_to_type_value("Entities", enum) == "entity"
    assert sections_mod._label_to_type_value("Analyses", enum) == "analysis"
    assert sections_mod._label_to_type_value("Syntheses", enum) == "synthesis"
    assert sections_mod._label_to_type_value("Open Questions", enum) == "open-question"
    # Recent Activity is virtual — no mapped type.
    assert sections_mod._label_to_type_value("Recent Activity", enum) is None


def test_label_to_type_value_falls_back_to_simple_plural():
    enum = ["topic"]
    assert sections_mod._label_to_type_value("Topics", enum) == "topic"
    assert sections_mod._label_to_type_value("Topic", enum) == "topic"
    assert sections_mod._label_to_type_value("Unknown", enum) is None


def test_build_sections_groups_pages_by_type(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    # Synthetic graph: one entity, two concepts, one stray (uncategorised).
    graph = Graph(
        nodes=[
            Node(slug="alpha", title="Alpha", type="entity"),
            Node(slug="beta", title="Beta", type="concept"),
            Node(slug="gamma", title="Gamma", type="concept"),
            Node(slug="orphan", title="Orphan", type=None),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_label = {s.label: s for s in sections}

    assert "Entities" in by_label
    assert "Concepts" in by_label
    assert [n.slug for n in by_label["Entities"].pages] == ["alpha"]
    assert {n.slug for n in by_label["Concepts"].pages} == {"beta", "gamma"}

    # Pages with no matching type land in Uncategorised, only present when non-empty.
    assert "Uncategorised" in by_label
    assert {n.slug for n in by_label["Uncategorised"].pages} == {"orphan"}


def test_build_sections_appends_unmapped_enum_types(research_wiki_project: Path):
    """Any enum type without a section gets a synthetic catch-all entry."""
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw.setdefault("frontmatter", {}).setdefault("enum", {})["type"] = [
        "entity",
        "concept",
        "novel-thing",  # not in index.sections
    ]
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(nodes=[Node(slug="x", title="X", type="novel-thing")])
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    assert "novel-thing" in by_slug
    assert [n.slug for n in by_slug["novel-thing"].pages] == ["x"]


def test_build_sections_object_form_with_explicit_types(research_wiki_project: Path):
    """The schema's array-of-objects form should let one section span multiple types."""
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["index"]["sections"] = [
        {"name": "Planning", "slug": "planning", "types": ["prd", "rfc", "decision"]},
        "Entities",
    ]
    raw["frontmatter"]["enum"]["type"] = ["prd", "rfc", "decision", "entity"]
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(
        nodes=[
            Node(slug="rfc-1", title="RFC 1", type="rfc"),
            Node(slug="decision-2", title="Decision 2", type="decision"),
            Node(slug="entity-a", title="Entity A", type="entity"),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    assert {n.slug for n in by_slug["planning"].pages} == {"rfc-1", "decision-2"}
    assert {n.slug for n in by_slug["entities"].pages} == {"entity-a"}


def test_display_name_for_type_uses_enum_display_names(research_wiki_project: Path):
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw.setdefault("frontmatter", {})["enumDisplayNames"] = {
        "type": {"open-question": "Open question"}
    }
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    assert sections_mod.display_name_for_type(cfg, "open-question") == "Open question"
    # Fallback: title-case + space.
    assert sections_mod.display_name_for_type(cfg, "plot-thread") == "Plot Thread"
    assert sections_mod.display_name_for_type(cfg, None) == ""


def test_config_surfaces_index_sections_and_type_enum(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    assert "Entities" in cfg.index_sections
    assert "entity" in cfg.type_enum
    assert isinstance(cfg.enum_display_names, dict)


def test_recent_activity_section_populated_from_updated_desc(research_wiki_project: Path):
    """A `Recent Activity` section in `index.sections` should be populated
    from the most-recently-updated nodes (desc), not from any `type` value."""
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(
        nodes=[
            Node(slug="old", title="Old", type="entity", updated="2025-01-01"),
            Node(slug="recent", title="Recent", type="concept", updated="2026-04-25"),
            Node(slug="newest", title="Newest", type="entity", updated="2026-04-26"),
            Node(slug="undated", title="Undated", type="concept"),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    assert "recent-activity" in by_slug
    recent = by_slug["recent-activity"].pages
    # Most recent first, undated nodes excluded.
    assert [n.slug for n in recent] == ["newest", "recent", "old"]


def test_sections_include_hidden_when_show_hidden_true(research_wiki_project: Path):
    """Regression — when `docsite.contentRoot` is widened past `.memex/`,
    every wiki page's path starts with `.memex/` (a dotted segment) and so
    its `Node.is_hidden` flag is True. Section assignment must respect
    `cfg.show_hidden` (default True) and not unconditionally skip those
    nodes — otherwise the user sees every typed page land in Uncategorised
    instead of its proper section.
    """
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"contentRoot": ".", "showHidden": True}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    # All wiki nodes are now "hidden" because the widened wiki_root sees
    # them under `.memex/wiki/...`.
    graph = Graph(
        nodes=[
            Node(slug=".memex/wiki/entities/x", title="X", type="entity", is_hidden=True),
            Node(slug=".memex/wiki/concepts/y", title="Y", type="concept", is_hidden=True),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    assert [n.slug for n in by_slug["entities"].pages] == [".memex/wiki/entities/x"]
    assert [n.slug for n in by_slug["concepts"].pages] == [".memex/wiki/concepts/y"]


def test_sections_skip_hidden_when_show_hidden_false(research_wiki_project: Path):
    """Companion — when `showHidden: false`, hidden nodes really should be
    excluded from section assignment (matches the graph builder's behaviour
    and respects the user's explicit opt-out)."""
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["docsite"] = {"showHidden": False}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(
        nodes=[
            Node(slug="entities/visible", title="V", type="entity", is_hidden=False),
            Node(slug=".hidden/secret", title="H", type="entity", is_hidden=True),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    assert [n.slug for n in by_slug["entities"].pages] == ["entities/visible"]


def test_folder_fallback_assigns_pages_by_first_segment(
    research_wiki_project: Path,
):
    """When a node has no `type` (or its type isn't in any section's
    `type_values`), fall back to matching the first non-dot folder
    segment of its slug against section slugs / kebab'd labels.
    Lets a page at `architecture/foo/README.md` land in an "Architecture"
    section without needing `type: architecture` on every file.
    """
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["index"]["sections"] = [
        "Entities",
        "Architecture",
        "Research",
        "Code Examples",
    ]
    raw["docsite"] = {"contentRoot": ".", "showHidden": True}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(
        nodes=[
            Node(slug="architecture/spec/foo", title="A1", type=None),
            Node(slug="architecture/spec/bar", title="A2", type="spec"),
            Node(slug="research/methodology/m1", title="R1", type=None),
            Node(slug="code-examples/snippet", title="C1", type=None),
            Node(slug=".memex/wiki/entities/x", title="E1", type="entity", is_hidden=True),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    # Type-based assignment still wins where the type matches.
    assert {n.slug for n in by_slug["entities"].pages} == {".memex/wiki/entities/x"}
    # Folder-based fallback for the rest.
    assert {n.slug for n in by_slug["architecture"].pages} == {
        "architecture/spec/foo",
        "architecture/spec/bar",  # `spec` type doesn't match any section, so folder wins
    }
    assert {n.slug for n in by_slug["research"].pages} == {"research/methodology/m1"}
    assert {n.slug for n in by_slug["code-examples"].pages} == {"code-examples/snippet"}
    # Nothing should land in Uncategorised — every node had either a
    # matching type or a matching folder.
    assert "uncategorised" not in by_slug


def test_folder_fallback_skips_dot_segments(research_wiki_project: Path):
    """The folder fallback should look past leading dot-folders so
    `.memex/wiki/entities/x` matches by `wiki`, not `.memex`."""
    cfg_path = research_wiki_project / "memex.config.json"
    raw = json.loads(cfg_path.read_text())
    raw["index"]["sections"] = ["Wiki"]
    raw["docsite"] = {"contentRoot": ".", "showHidden": True}
    cfg_path.write_text(json.dumps(raw))
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(
        nodes=[
            Node(slug=".memex/wiki/entities/x", title="X", type=None, is_hidden=True),
        ]
    )
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    assert [n.slug for n in by_slug["wiki"].pages] == [".memex/wiki/entities/x"]


def test_synthetic_sections_marked(research_wiki_project: Path):
    """Auto-appended (uncovered enum) and Uncategorised sections carry an
    `is_synthetic` flag so the sidebar can elide them when empty."""
    cfg = cfg_mod.load(start=research_wiki_project)
    graph = Graph(nodes=[Node(slug="x", title="X", type="rule")])
    sections = sections_mod.build_sections(cfg, graph)
    by_slug = {s.slug: s for s in sections}
    # `rule` is in the enum but not in research-wiki's index.sections list.
    # research-wiki *does* have a section that maps to "rule" though — check
    # whether it was auto-appended or already declared.
    declared_labels = set(cfg.index_sections)
    if "Rules" in declared_labels or "Rule" in declared_labels:
        # If a profile change made `rule` a declared section, skip — the
        # invariant under test is "auto-appended sections are flagged".
        return
    rule_section = next(s for s in sections if s.type_values == ["rule"])
    assert rule_section.is_synthetic is True
    # Uncategorised, when emitted, is also synthetic.
    if "uncategorised" in by_slug:
        assert by_slug["uncategorised"].is_synthetic is True
