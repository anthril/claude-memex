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
        (wiki_root / slug / "README.md").resolve(),
    ]
    # Top-level `index` slug also falls back to `README.md` at the root.
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
    """Resolve a relative link against a source page's slug.

    `target` is the raw link target as written in the source markdown
    (e.g., `../foo`, `subdir/page`, `page#heading`, `../schemas/x.json`).
    Returns the canonical slug-or-asset-path it points to, or None if no
    file matches.

    Two-pass resolution:
      1. Treat the target as a markdown page (strip `.md` if present, try
         `slug_to_path`). Returns a canonical slug.
      2. If that fails, treat the target as a literal asset (preserve any
         extension, check that the file exists under `wiki_root`). Returns
         the asset path verbatim — the page route will serve it via
         `FileResponse` with a guessed content-type.
    """
    target = target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#", "/")):
        return None

    fragment = ""
    if "#" in target:
        target, fragment = target.split("#", 1)

    md_target = target[:-3] if target.endswith(".md") else target

    source_dir = Path(source_slug).parent if "/" in source_slug else Path("")

    def _normalise(rel: str) -> str | None:
        combined = (source_dir / rel).as_posix()
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
        return "/".join(parts) or "index"

    # Pass 1: markdown page resolution.
    md_slug = _normalise(md_target)
    if md_slug is not None and slug_to_path(md_slug, wiki_root) is not None:
        return f"{md_slug}#{fragment}" if fragment else md_slug

    # Pass 1b: folder resolution. If the link points at a real directory
    # under wiki_root, the live server's `_folder_response` will render an
    # auto-generated folder index for it — don't mark such links broken.
    if md_slug is not None:
        folder = (wiki_root / md_slug).resolve()
        try:
            folder.relative_to(wiki_root.resolve())
        except ValueError:
            pass
        else:
            if folder.is_dir():
                return f"{md_slug}#{fragment}" if fragment else md_slug

    # Pass 2: literal asset resolution. Skip when the original target had no
    # extension (we already tried .md above) — only kicks in for things like
    # `.json`, `.svg`, `.png`, `.pdf`, `.csv`, etc.
    if "." in Path(target).name and not target.endswith(".md"):
        asset_slug = _normalise(target)
        if asset_slug is not None:
            asset_path = (wiki_root / asset_slug).resolve()
            try:
                asset_path.relative_to(wiki_root.resolve())
            except ValueError:
                return None
            if asset_path.is_file():
                return f"{asset_slug}#{fragment}" if fragment else asset_slug

    return None
