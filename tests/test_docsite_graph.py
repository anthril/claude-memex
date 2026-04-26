"""Tests for the link graph builder (Phase 2)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("yaml")

from memex_docsite import graph  # noqa: E402


def _seed(root: Path) -> Path:
    wiki = root / ".memex"
    wiki.mkdir()
    (wiki / "index.md").write_text(
        "---\ntitle: Home\n---\n\n"
        "See [[alpha]] and [beta page](beta).\n"
    )
    (wiki / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\nLinks to [[beta]] and [[gamma]].\n"
    )
    (wiki / "beta.md").write_text(
        "---\ntitle: Beta\ntype: concept\n---\n\nA leaf node.\n"
    )
    (wiki / "gamma.md").write_text(
        "---\ntitle: Gamma\ntype: concept\n---\n\nNo outgoing references.\n"
    )
    (wiki / "lonely.md").write_text(
        "---\ntitle: Lonely\n---\n\nNo links in or out.\n"
    )
    return wiki


def test_graph_builds_nodes_and_edges(tmp_path: Path):
    wiki = _seed(tmp_path)
    g = graph.build(wiki)
    slugs = {n.slug for n in g.nodes}
    assert slugs == {"index", "alpha", "beta", "gamma", "lonely"}
    edges = {(e.source, e.target) for e in g.edges}
    assert ("index", "alpha") in edges
    assert ("index", "beta") in edges
    assert ("alpha", "beta") in edges
    assert ("alpha", "gamma") in edges


def test_graph_summary(tmp_path: Path):
    wiki = _seed(tmp_path)
    g = graph.build(wiki)
    # `lonely` has no inbound or outbound: orphan + dead-end.
    assert "lonely" in g.summary.orphans
    assert "lonely" in g.summary.dead_ends
    # `index` has no inbound (only outbound) → orphan but not dead-end.
    assert "index" in g.summary.orphans
    assert "index" not in g.summary.dead_ends
    # `gamma` has no outbound → dead-end.
    assert "gamma" in g.summary.dead_ends
    # No node has 5+ inbound in this fixture.
    assert g.summary.hubs == []


def test_graph_skips_broken_links(tmp_path: Path):
    wiki = tmp_path / ".memex"
    wiki.mkdir()
    (wiki / "page.md").write_text("Refers to [[nonexistent]] which doesn't exist.")
    g = graph.build(wiki)
    assert all(e.target != "nonexistent" for e in g.edges)


def test_graph_to_dict_round_trip(tmp_path: Path):
    wiki = _seed(tmp_path)
    g = graph.build(wiki)
    payload = graph.to_dict(g)
    assert payload["summary"]["node_count"] == 5
    assert payload["summary"]["edge_count"] == len(g.edges)
    assert {n["slug"] for n in payload["nodes"]} == {"index", "alpha", "beta", "gamma", "lonely"}


def test_graph_mermaid_text(tmp_path: Path):
    wiki = _seed(tmp_path)
    text = graph.to_mermaid(graph.build(wiki))
    assert text.startswith("graph LR")
    assert "alpha" in text
    assert "-->" in text


def test_graph_respects_show_hidden(tmp_path: Path):
    wiki = _seed(tmp_path)
    hidden = wiki / ".rules"
    hidden.mkdir()
    (hidden / "rule.md").write_text("Secret rule.")
    g_with = graph.build(wiki, show_hidden=True)
    g_without = graph.build(wiki, show_hidden=False)
    assert any(n.slug == ".rules/rule" for n in g_with.nodes)
    assert all(n.slug != ".rules/rule" for n in g_without.nodes)
