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


# Section slugs that should always render as "meta" (their own group at the
# bottom of the sidebar, separated from curated + authored content).
_META_SLUGS = frozenset({"recent-activity", "uncategorised"})


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

    @property
    def kind(self) -> str:
        """Classify the section for sidebar grouping.

        - "curated" — maps to a `frontmatter.enum.type` value, so its pages
          are LLM-curated wiki content (entities, concepts, summaries…).
        - "authored" — folder-only match, so its pages are first-party
          content the human / Claude write directly (architecture, research,
          data, etc.).
        - "meta"     — virtual / catch-all sections (Recent Activity,
          Uncategorised). Rendered separately at the bottom of the nav.
        """
        if self.slug in _META_SLUGS:
            return "meta"
        if self.type_values:
            return "curated"
        return "authored"


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


def _section_for_slug(slug: str, folder_to_section: dict) -> Section | None:
    """Return the section a slug maps to via folder convention, or None.

    Walks the slug's path segments left-to-right and returns the first
    folder match. Skips leading dot-folders (so `.memex/wiki/entities/x`
    looks at `wiki` first, then `entities`) — the dot-folder itself is
    metadata rather than a content section.
    """
    if not slug:
        return None
    parts = [p for p in slug.split("/") if p and not p.startswith(".")]
    for part in parts:
        hit = folder_to_section.get(part.casefold())
        if hit is not None:
            return hit
    return None


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

    # Assign pages. A page lands in the first section that matches by:
    # 1. `Node.type` ∈ section.type_values  (the strict typed path)
    # 2. first folder segment of `Node.slug` matches the section slug or its
    #    kebab'd label (the folder-fallback path) — lets a page at
    #    `architecture/foo.md` land in an "Architecture" section without
    #    needing a `type: architecture` frontmatter on every file.
    # Pages with no type and no matching folder segment fall through to
    # "Uncategorised" (only kept if non-empty).
    type_to_section: dict[str, Section] = {}
    folder_to_section: dict[str, Section] = {}
    for s in sections:
        for t in s.type_values:
            type_to_section.setdefault(t, s)
        # The section's slug + a kebab'd version of its label are both valid
        # folder matches. Skip dot-prefixed labels (Open Questions / Rules
        # — those folders are dot-folders that have dedicated UI elsewhere).
        folder_keys = {s.slug.casefold(), slugify_label(s.label)}
        for key in folder_keys:
            if key and not key.startswith("."):
                folder_to_section.setdefault(key, s)

    uncategorised = Section(
        slug="uncategorised", label="Uncategorised", is_synthetic=True
    )
    # Respect `cfg.show_hidden` — when a project widens `docsite.contentRoot`
    # past `.memex/`, every wiki page's path starts with `.memex/` (a dotted
    # segment) and so flags `is_hidden=True`. Skipping those would hide the
    # entire wiki from the sections nav. The graph builder already honours
    # show_hidden when populating nodes; this loop should mirror it.
    show_hidden = bool(getattr(cfg, "show_hidden", True))
    for node in graph.nodes:
        if node.is_hidden and not show_hidden:
            continue
        target = type_to_section.get(node.type or "")
        if target is None:
            # Fallback: first folder segment of the slug, skipping any
            # leading dot-folder (so `.memex/wiki/entities/x` matches by
            # `wiki` first, then by deeper segments — but section assignment
            # only checks the non-dot top-level segment).
            target = _section_for_slug(node.slug, folder_to_section)
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
    # Mirror the show_hidden gate above so wiki pages under `.memex/` show
    # up when `contentRoot` is widened.
    for s in sections:
        if s.slug not in _RECENT_ACTIVITY_SLUGS:
            continue
        recent = [
            n for n in graph.nodes
            if n.updated and (show_hidden or not n.is_hidden)
        ]
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


_FOLDER_INDEX_NAMES = frozenset({"index", "readme"})


@dataclass(slots=True)
class SectionTreeNode:
    """Recursive tree node for the section landing page.

    A folder node has `is_folder=True`; a leaf (page) node has it False.
    A folder may also carry `slug`/`title` of its landing page (when
    `<folder>/index.md` or `<folder>/README.md` exists) so the template
    can hyperlink the folder summary itself.
    """

    name: str
    slug: str | None = None  # leaf: page slug; folder: optional landing-page slug
    title: str | None = None
    type: str | None = None
    children: list[SectionTreeNode] = field(default_factory=list)
    is_folder: bool = False


def build_section_tree(pages: list[Node]) -> SectionTreeNode:
    """Group a flat list of section pages into a recursive folder tree.

    Pages whose final slug segment is `index` or `README` (case-insensitive)
    are attached to their parent folder as the folder's *landing page*
    rather than as a child leaf — clicking the folder summary navigates
    to that page. Other pages become leaves under their folder.

    Files at the same level sort first by title; folders sort after,
    alphabetically. The root node has empty `name` and is iterated by
    the template via `root.children`.
    """
    root = SectionTreeNode(name="")

    def find_or_create_folder(cursor: SectionTreeNode, name: str) -> SectionTreeNode:
        existing = next(
            (c for c in cursor.children if c.is_folder and c.name == name),
            None,
        )
        if existing is None:
            existing = SectionTreeNode(name=name, is_folder=True)
            cursor.children.append(existing)
        return existing

    def insert(parts: list[str], page: Node) -> None:
        leaf_name = parts[-1]
        if len(parts) >= 1 and leaf_name.casefold() in _FOLDER_INDEX_NAMES:
            # Treat as a folder landing page. Find/create the parent
            # folder and attach the page's slug/title to it.
            if len(parts) == 1:
                # `index` or `README` at the wiki root — keep as a leaf
                # so it still appears (no parent folder to attach to).
                root.children.append(
                    SectionTreeNode(
                        name=leaf_name,
                        slug=page.slug,
                        title=page.title,
                        type=page.type,
                    )
                )
                return
            cursor = root
            for segment in parts[:-2]:
                cursor = find_or_create_folder(cursor, segment)
            folder = find_or_create_folder(cursor, parts[-2])
            folder.slug = page.slug
            folder.title = page.title
            folder.type = page.type
            return

        # Regular leaf — walk each non-leaf segment, creating folder
        # nodes lazily, then add the page as a child.
        cursor = root
        for segment in parts[:-1]:
            cursor = find_or_create_folder(cursor, segment)
        cursor.children.append(
            SectionTreeNode(
                name=leaf_name,
                slug=page.slug,
                title=page.title,
                type=page.type,
            )
        )

    for page in pages:
        parts = [p for p in page.slug.split("/") if p]
        if not parts:
            continue
        insert(parts, page)

    def sort_recursive(node: SectionTreeNode) -> None:
        # Folders sort before leaves (so folder hierarchy reads top-down);
        # within each kind, alphabetical by display label.
        node.children.sort(
            key=lambda n: (
                not n.is_folder,
                (n.title or n.name).casefold(),
            )
        )
        for child in node.children:
            if child.is_folder:
                sort_recursive(child)

    sort_recursive(root)
    return root


def display_name_for_type(cfg, type_value: str | None) -> str:
    """Return the configured display name for an enum type value, or a
    title-cased fallback."""
    if not type_value:
        return ""
    type_map = (cfg.enum_display_names or {}).get("type") or {}
    if type_value in type_map:
        return str(type_map[type_value])
    return type_value.replace("-", " ").title()
