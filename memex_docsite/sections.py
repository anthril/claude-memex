"""Section grouping for the docsite's profile-driven nav.

A `Section` corresponds to one entry in `memex.config.json#/index.sections`
optionally bridged to one or more `frontmatter.enum.type` values. The
docsite renders one sidebar entry per section and one landing page at
`/sections/<slug>/` per section.

The shape supports both the array-of-strings shorthand
(`["Entities", "Concepts", ...]`) and the array-of-objects form added in
the schema for many-to-one cases like `engineering-ops` "Planning" ↔
`prd|rfc|decision`.

Page→section assignment cascades:
1. Match each `index.sections` entry to one or more `frontmatter.enum.type`
   values (explicit `types: [...]` wins; otherwise the plural-map heuristic).
2. Walk the cached graph nodes; assign each node to the first section
   whose type set contains its `Node.type`.
3. Append any enum type not yet covered by a section as its own
   synthetic section so nothing is silently dropped.
4. Pages with no `type` and no folder hint fall through to an
   "Uncategorised" bucket which is only emitted when non-empty.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .graph import Graph, Node

# Explicit overrides for English plurals that don't degenerate cleanly via
# `rstrip("s")`. Keys are lowercased section labels; values are the matching
# `frontmatter.enum.type` value.
_PLURAL_OVERRIDES: dict[str, str | None] = {
    "analyses": "analysis",
    "syntheses": "synthesis",
    "entities": "entity",
    "hypotheses": "hypothesis",
    "summaries": "summary",
    "open questions": "open-question",
    "recent activity": None,  # virtual — sourced from `updated:` not from type
    "chapter summaries": "summary",
    "plot threads": "plot-thread",
    "literature reviews": "literature-review",
    "experiments": "experiment",
    "evaluations": "evaluation",
    "methodologies": "methodology",
    "incidents": "incident",
    "runbooks": "runbook",
    "processes": "process",
    "environments": "environment",
    "agents": "agent",
    "workflows": "workflow",
    "workers": "worker",
    "integrations": "integration",
}


@dataclass(slots=True)
class Section:
    slug: str
    label: str
    type_values: list[str] = field(default_factory=list)
    pages: list[Node] = field(default_factory=list)
    is_synthetic: bool = False  # True for auto-appended (uncovered enum) + Uncategorised

    @property
    def count(self) -> int:
        return len(self.pages)

    @property
    def is_virtual(self) -> bool:
        """True for sections with no underlying type (e.g. Recent Activity)."""
        return not self.type_values


# Slugs whose pages come from `frontmatter.updated` desc, not from a type.
_RECENT_ACTIVITY_SLUGS = frozenset({"recent-activity"})

# Cap on the number of pages a virtual "recent activity" section surfaces.
_RECENT_ACTIVITY_LIMIT = 25


_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


def slugify_label(label: str) -> str:
    return _SLUGIFY_RE.sub("-", label.casefold()).strip("-") or "section"


def _label_to_type_value(label: str, type_enum: list[str]) -> str | None:
    """Best-effort map from an `index.sections` heading to a single
    `frontmatter.enum.type` value. Returns None for virtual sections
    (e.g. Recent Activity) and labels that don't match any enum value."""
    if not type_enum:
        return None
    lower = label.casefold().strip()
    if lower in _PLURAL_OVERRIDES:
        return _PLURAL_OVERRIDES[lower]
    enum_lower = {t.casefold(): t for t in type_enum}
    if lower in enum_lower:
        return enum_lower[lower]
    if lower.endswith("s") and lower[:-1] in enum_lower:
        return enum_lower[lower[:-1]]
    if lower.endswith("es") and lower[:-2] in enum_lower:
        return enum_lower[lower[:-2]]
    return None


def _section_specs(
    raw_sections: list,
    type_enum: list[str],
) -> list[tuple[str, str, list[str]]]:
    """Normalise `index.sections` into `(slug, label, [type_value...])` tuples.

    Accepts either the array-of-strings shorthand or the array-of-objects
    form. Explicit `types: [...]` always wins over the plural-map heuristic.
    """
    specs: list[tuple[str, str, list[str]]] = []
    for entry in raw_sections:
        if isinstance(entry, str):
            label = entry
            slug = slugify_label(label)
            mapped = _label_to_type_value(label, type_enum)
            specs.append((slug, label, [mapped] if mapped else []))
        elif isinstance(entry, dict):
            label = str(entry.get("name") or "")
            if not label:
                continue
            slug = str(entry.get("slug") or slugify_label(label))
            types_raw = entry.get("types")
            if isinstance(types_raw, list):
                types = [str(t) for t in types_raw if isinstance(t, str)]
            else:
                mapped = _label_to_type_value(label, type_enum)
                types = [mapped] if mapped else []
            specs.append((slug, label, types))
    return specs


def build_sections(
    cfg,  # DocsiteConfig — avoid circular import
    graph: Graph,
) -> list[Section]:
    """Build the ordered list of `Section`s the docsite should render."""
    raw_sections = cfg.index_sections or []
    type_enum = list(cfg.type_enum or [])

    specs = _section_specs(raw_sections, type_enum)

    sections: list[Section] = []
    seen_types: set[str] = set()
    for slug, label, types in specs:
        sections.append(Section(slug=slug, label=label, type_values=list(types)))
        seen_types.update(types)

    # Append any enum type not covered by an explicit section so nothing
    # drops silently. Marked synthetic so the sidebar can elide them when
    # they're empty.
    for enum_value in type_enum:
        if enum_value in seen_types:
            continue
        label = enum_value.replace("-", " ").title()
        sections.append(
            Section(
                slug=slugify_label(enum_value),
                label=label,
                type_values=[enum_value],
                is_synthetic=True,
            )
        )
        seen_types.add(enum_value)

    # Assign pages. A page lands in the first section whose `type_values`
    # contains its `Node.type`. Pages with no type or no matching section
    # fall through to "Uncategorised" (only kept if non-empty).
    type_to_section: dict[str, Section] = {}
    for s in sections:
        for t in s.type_values:
            type_to_section.setdefault(t, s)

    uncategorised = Section(
        slug="uncategorised", label="Uncategorised", is_synthetic=True
    )
    for node in graph.nodes:
        if node.is_hidden:
            continue
        target = type_to_section.get(node.type or "")
        if target is not None:
            target.pages.append(node)
        else:
            uncategorised.pages.append(node)

    if uncategorised.pages:
        sections.append(uncategorised)

    # Sort each section's page list by title for stable rendering.
    for s in sections:
        s.pages.sort(key=lambda n: n.title.casefold())

    # Populate virtual "Recent Activity" sections from `frontmatter.updated`
    # desc — these have empty `type_values` so they wouldn't otherwise pick
    # up any pages. Only nodes with a parseable `updated` are eligible.
    for s in sections:
        if s.slug not in _RECENT_ACTIVITY_SLUGS:
            continue
        recent = [n for n in graph.nodes if n.updated and not n.is_hidden]
        recent.sort(key=lambda n: n.updated or "", reverse=True)
        s.pages = recent[:_RECENT_ACTIVITY_LIMIT]

    return sections


def suggest_section(
    sections: dict[str, set[str]] | dict[str, object],
    rel_path: str,
    page_type: str | None = None,
) -> str | None:
    """Best-effort guess at which `index.sections` heading a page belongs to.

    Mirrors `hooks/scripts/_lib/index_parse.suggest_section`. Two copies
    exist for the same reason `frontmatter.py` is duplicated — hook
    scripts can't import the optional `memex_docsite` package. Parity is
    asserted by `tests/test_docsite_sections_parity.py`.
    """
    if not sections:
        return None
    section_names = list(sections.keys())

    def match(candidate: str) -> str | None:
        if not candidate:
            return None
        cand_lower = candidate.lower()
        for name in section_names:
            nl = name.lower()
            if nl == cand_lower or nl == cand_lower + "s" or nl == cand_lower + "es":
                return name
            if nl.rstrip("s") == cand_lower:
                return name
        return None

    if page_type:
        hit = match(page_type)
        if hit:
            return hit

    first_segment = rel_path.split("/", 1)[0]
    hit = match(first_segment)
    if hit:
        return hit

    return None


def display_name_for_type(cfg, type_value: str | None) -> str:
    """Return the configured display name for an enum type value, or a
    title-cased fallback."""
    if not type_value:
        return ""
    type_map = (cfg.enum_display_names or {}).get("type") or {}
    if type_value in type_map:
        return str(type_map[type_value])
    return type_value.replace("-", " ").title()
