"""Build the navigation tree shown in the sidebar.

A flat scan of every `.md` file under the wiki root, grouped by folder,
sorted alphabetically with `index.md`/`README.md` floated to the top of
each folder. Hidden folders (those starting with `.`) are surfaced when
`show_hidden` is true; otherwise omitted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import resolver

INDEX_NAMES = ("index.md", "README.md", "AGENTS.md")


@dataclass(slots=True)
class TreeNode:
    name: str
    slug: str | None = None  # None for non-leaf folders
    title: str | None = None
    children: list[TreeNode] = field(default_factory=list)
    is_folder: bool = False
    is_hidden: bool = False


def _is_hidden(parts: tuple[str, ...]) -> bool:
    return any(p.startswith(".") and p not in (".", "..") for p in parts)


def build(
    wiki_root: Path,
    *,
    show_hidden: bool = True,
    is_ignored=None,
) -> TreeNode:
    """Walk the wiki and return a single root TreeNode."""
    root = wiki_root.resolve()
    root_node = TreeNode(name=root.name, is_folder=True)

    folders: dict[str, TreeNode] = {"": root_node}

    files: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        rel_parts = rel.parts
        if not show_hidden and _is_hidden(rel_parts):
            continue
        if is_ignored is not None and is_ignored(rel.as_posix()):
            continue
        files.append(path)

    for file_path in files:
        rel = file_path.relative_to(root)
        parts = rel.parts
        # Build / locate parent folder nodes.
        current = root_node
        for depth, part in enumerate(parts[:-1]):
            key = "/".join(parts[: depth + 1])
            existing = folders.get(key)
            if existing is None:
                existing = TreeNode(
                    name=part,
                    is_folder=True,
                    is_hidden=part.startswith("."),
                )
                folders[key] = existing
                current.children.append(existing)
            current = existing
        # Add the file as a leaf.
        slug = resolver.path_to_slug(file_path, root)
        title = parts[-1][:-3]  # filename minus .md; renderer will refine if it parses fm
        leaf = TreeNode(name=parts[-1], slug=slug, title=title)
        current.children.append(leaf)

    _sort_recursive(root_node)
    return root_node


def _sort_recursive(node: TreeNode) -> None:
    def key(n: TreeNode) -> tuple[int, int, str]:
        # Folders after files within their depth, but index/README files go first.
        is_index = (not n.is_folder) and n.name in INDEX_NAMES
        return (0 if is_index else (2 if n.is_folder else 1), 0, n.name.lower())

    node.children.sort(key=key)
    for child in node.children:
        _sort_recursive(child)
