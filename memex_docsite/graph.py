"""Link graph builder.

Walks every `.md` file under the wiki root, parses outgoing links
(both standard `[text](path)` and wikilinks `[[slug]]`), resolves them
to canonical slugs, and emits nodes + edges + orphans/hubs/dead-ends.

Output formats:
- `to_dict(...)` — serialisable shape consumed by `/api/graph`.
- `to_mermaid(...)` — text suitable for Mermaid live-render.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import frontmatter, resolver

LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?://|mailto:|#)([^)\s#]+)(?:#[^)]*)?\)")
WIKILINK_RE = re.compile(resolver.WIKILINK_PATTERN)


def _coerce_iso(value: object) -> str | None:
    """Coerce a frontmatter date/datetime/string into an ISO-8601 string.

    PyYAML parses bare `updated: 2026-04-23` as `datetime.date`; quoted
    values come through as `str`. We accept both and reject anything else.
    """
    import datetime as _dt

    if isinstance(value, str):
        return value
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    return None


@dataclass(slots=True)
class Node:
    slug: str
    title: str
    type: str | None = None
    is_hidden: bool = False
    updated: str | None = None


@dataclass(slots=True)
class Edge:
    source: str
    target: str


@dataclass(slots=True)
class GraphSummary:
    orphans: list[str] = field(default_factory=list)
    hubs: list[str] = field(default_factory=list)
    dead_ends: list[str] = field(default_factory=list)
    edge_count: int = 0
    node_count: int = 0


@dataclass(slots=True)
class Graph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    summary: GraphSummary = field(default_factory=GraphSummary)


def build(
    wiki_root: Path,
    *,
    show_hidden: bool = True,
    hub_threshold: int = 5,
    is_ignored=None,
) -> Graph:
    """Walk the wiki, build a Graph."""
    wiki_root = wiki_root.resolve()
    nodes: dict[str, Node] = {}

    for path in sorted(wiki_root.rglob("*.md")):
        rel = path.relative_to(wiki_root)
        is_hidden = any(p.startswith(".") for p in rel.parts)
        if not show_hidden and is_hidden:
            continue
        if is_ignored is not None and is_ignored(rel.as_posix()):
            continue
        slug = resolver.path_to_slug(path, wiki_root)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, _ = frontmatter.split(content)
        fm = fm or {}
        title = (
            fm.get("title")
            or _first_heading(content)
            or rel.parts[-1][:-3].replace("-", " ").title()
        )
        nodes[slug] = Node(
            slug=slug,
            title=str(title),
            type=fm.get("type"),
            is_hidden=is_hidden,
            updated=_coerce_iso(fm.get("updated")),
        )

    edges: list[Edge] = []
    inbound: dict[str, set[str]] = defaultdict(set)
    outbound: dict[str, set[str]] = defaultdict(set)

    for slug, _node in nodes.items():
        resolved_path = resolver.slug_to_path(slug, wiki_root)
        if resolved_path is None:
            continue
        try:
            content = resolved_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        _, body = frontmatter.split(content)
        for target in _outgoing_targets(body, slug, wiki_root):
            if target == slug or target not in nodes:
                continue
            edges.append(Edge(source=slug, target=target))
            inbound[target].add(slug)
            outbound[slug].add(target)

    summary = GraphSummary(node_count=len(nodes), edge_count=len(edges))
    summary.orphans = sorted(slug for slug in nodes if not inbound[slug])
    summary.dead_ends = sorted(slug for slug in nodes if not outbound[slug])
    summary.hubs = sorted(
        (slug for slug, refs in inbound.items() if len(refs) >= hub_threshold),
        key=lambda s: -len(inbound[s]),
    )

    return Graph(nodes=list(nodes.values()), edges=edges, summary=summary)


def _outgoing_targets(body: str, source_slug: str, wiki_root: Path):
    """Yield canonical target slugs referenced from `body`."""
    for match in LINK_RE.finditer(body):
        url = match.group(2)
        target = resolver.resolve_relative(url, source_slug, wiki_root)
        if target is None:
            continue
        if "#" in target:
            target = target.split("#", 1)[0]
        yield target

    for match in WIKILINK_RE.finditer(body):
        target = match.group(1).strip()
        if resolver.slug_to_path(target, wiki_root) is None:
            continue
        yield target


def _first_heading(content: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else None


def backlinks_for(graph: Graph, slug: str) -> list[Node]:
    """Return every node whose outgoing edges point to `slug`, sorted by title."""
    by_slug = {n.slug: n for n in graph.nodes}
    sources = sorted({e.source for e in graph.edges if e.target == slug})
    return [by_slug[s] for s in sources if s in by_slug]


def to_dict(graph: Graph) -> dict:
    return {
        "nodes": [asdict(n) for n in graph.nodes],
        "edges": [asdict(e) for e in graph.edges],
        "summary": asdict(graph.summary),
    }


def to_mermaid(graph: Graph, *, max_edges: int = 500) -> str:
    """Render a Mermaid `graph LR` block. Truncated past `max_edges` for legibility."""
    lines = ["graph LR"]
    for node in graph.nodes:
        safe_id = _safe_id(node.slug)
        label = node.title.replace('"', "'")
        lines.append(f'  {safe_id}["{label}"]')
    for edge in graph.edges[:max_edges]:
        lines.append(f"  {_safe_id(edge.source)} --> {_safe_id(edge.target)}")
    if len(graph.edges) > max_edges:
        lines.append(f"  %% truncated: {len(graph.edges) - max_edges} more edge(s)")
    return "\n".join(lines)


_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9]")


def _safe_id(slug: str) -> str:
    """Mermaid node IDs can't contain `/` or other chars; collapse to underscores."""
    return _SAFE_ID_RE.sub("_", slug) or "n"
