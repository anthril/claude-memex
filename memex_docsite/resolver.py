"""Link resolution: wikilinks, relative links, and slug normalisation.

A page's slug is its path relative to the wiki root, without the `.md`
extension. URL paths in the docsite map 1:1 to slugs.
"""
from __future__ import annotations

from pathlib import Path

WIKILINK_PATTERN = r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]"


def path_to_slug(file_path: Path, wiki_root: Path) -> str:
    """Convert an absolute `.md` file path to a docsite slug.

    Examples:
        wiki_root/index.md       -> "index"
        wiki_root/sub/page.md    -> "sub/page"
        wiki_root/sub/index.md   -> "sub/index"
    """
    rel = file_path.resolve().relative_to(wiki_root.resolve())
    parts = list(rel.parts)
    if parts[-1].endswith(".md"):
        parts[-1] = parts[-1][:-3]
    return "/".join(parts)


def slug_to_path(slug: str, wiki_root: Path) -> Path | None:
    """Resolve a slug to an existing markdown file under `wiki_root`.

    Tries (in order): exact `.md`, folder `index.md`, folder `README.md`.
    The README fallback is what makes plain repos browseable without
    inventing a synthetic top-level `index.md`. Returns None if none
    exist. Refuses paths that escape the wiki root (defends against `..`
    traversal).
    """
    slug = slug.strip("/")
    if not slug:
        slug = "index"
    root_resolved = wiki_root.resolve()
    candidates = [
        (wiki_root / f"{slug}.md").resolve(),
        (wiki_root / slug / "index.md").resolve(),
    ]
    # Top-level `index` slug also falls back to `README.md` at the root —
    # most repos have a README.md and no synthetic index.
    if slug == "index":
        candidates.append((wiki_root / "README.md").resolve())
    for candidate in candidates:
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def slug_to_url(slug: str) -> str:
    """Convert a slug to a URL path. Folder index slugs collapse to the folder URL."""
    slug = slug.strip("/")
    if slug == "index" or slug == "":
        return "/"
    if slug.endswith("/index"):
        return f"/{slug[:-len('index')]}"
    return f"/{slug}"


def resolve_relative(target: str, source_slug: str, wiki_root: Path) -> str | None:
    """Resolve a relative markdown link against a source page's slug.

    `target` is the raw link target as written in the source markdown
    (e.g., `../foo`, `subdir/page`, `page#heading`). Returns the canonical
    slug it points to, or None if no file matches.
    """
    target = target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#", "/")):
        return None

    fragment = ""
    if "#" in target:
        target, fragment = target.split("#", 1)

    if target.endswith(".md"):
        target = target[:-3]

    source_dir = Path(source_slug).parent if "/" in source_slug else Path("")
    combined = (source_dir / target).as_posix()
    parts: list[str] = []
    for part in combined.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            else:
                return None  # escapes the wiki root
            continue
        parts.append(part)
    candidate_slug = "/".join(parts) or "index"

    if slug_to_path(candidate_slug, wiki_root) is None:
        return None
    return f"{candidate_slug}#{fragment}" if fragment else candidate_slug
