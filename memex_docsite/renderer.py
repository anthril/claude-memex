"""Markdown → HTML renderer with wikilink + relative-link rewriting.

Built on top of `mistune` (added via the `docsite` optional-dep group).
The renderer is a pure function: feed it markdown + the slug of the page
being rendered, get back an HTML string with frontmatter, broken links,
and the page's title surfaced separately.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import mistune

from . import frontmatter, resolver

WIKILINK_RE = re.compile(resolver.WIKILINK_PATTERN)


@dataclass(slots=True)
class RenderedPage:
    slug: str
    title: str
    html: str
    frontmatter: dict
    headings: list[tuple[int, str, str]] = field(default_factory=list)
    """List of (level, slug, text) for table-of-contents generation."""
    broken_links: list[str] = field(default_factory=list)


def _slugify_heading(text: str) -> str:
    """GFM-style heading slug: lowercase, ASCII letters/digits/hyphens only."""
    cleaned = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"[\s_]+", "-", cleaned).strip("-") or "section"


class _DocsiteRenderer(mistune.HTMLRenderer):
    """mistune renderer that captures headings + rewrites links."""

    def __init__(
        self,
        *,
        source_slug: str,
        wiki_root: Path,
        broken_links: list[str],
        headings: list[tuple[int, str, str]],
    ) -> None:
        super().__init__()
        self._source_slug = source_slug
        self._wiki_root = wiki_root
        self._broken = broken_links
        self._headings = headings
        self._heading_slugs: set[str] = set()

    def heading(self, text: str, level: int, **attrs) -> str:
        # mistune passes the inline-rendered HTML; strip tags for slug + ToC text.
        plain = re.sub(r"<[^>]+>", "", text).strip()
        base = _slugify_heading(plain)
        slug = base
        n = 2
        while slug in self._heading_slugs:
            slug = f"{base}-{n}"
            n += 1
        self._heading_slugs.add(slug)
        self._headings.append((level, slug, plain))
        return f'<h{level} id="{slug}">{text}</h{level}>\n'

    def link(self, text: str, url: str, title: str | None = None) -> str:
        rewritten = self._rewrite_url(url)
        if rewritten is None:
            self._broken.append(url)
            return f'<a class="memex-broken" href="{mistune.escape(url)}" title="broken link">{text}</a>'
        title_attr = f' title="{mistune.escape(title)}"' if title else ""
        return f'<a href="{mistune.escape(rewritten)}"{title_attr}>{text}</a>'

    def _rewrite_url(self, url: str) -> str | None:
        url = url.strip()
        if not url:
            return None
        if url.startswith(("http://", "https://", "mailto:", "/", "#")):
            return url
        # Relative markdown link
        target = resolver.resolve_relative(url, self._source_slug, self._wiki_root)
        if target is None:
            return None
        if "#" in target:
            slug, frag = target.split("#", 1)
            return f"{resolver.slug_to_url(slug)}#{frag}"
        return resolver.slug_to_url(target)


def _expand_wikilinks(markdown: str, source_slug: str, wiki_root: Path, broken: list[str]) -> str:
    """Convert `[[slug]]` and `[[slug|display]]` to standard `[display](url)`.

    Resolution cascade for the target slug:
      1. Absolute lookup — `slug_to_path(target, wiki_root)`. Behaves like
         a wiki where every page has a unique slug from the wiki root.
      2. Sibling-relative — `slug_to_path("<source-dir>/<target>", wiki_root)`.
         Lets a page at `architecture/foo/index.md` write
         `[[criterion-1-local-learning]]` and have it resolve to a sibling
         file at `architecture/foo/criterion-1-local-learning.md`. This is
         the convention most users actually expect (Obsidian-style), and
         matches how `resolve_relative` already works for markdown links.
      3. Ancestor walk — try each ancestor folder of the source page in
         turn. Lets `[[shared-helper]]` from a deeply-nested page resolve
         to a `shared-helper.md` higher in the tree.
    """

    source_dir = source_slug.rsplit("/", 1)[0] if "/" in source_slug else ""

    def _resolve_target(target_slug: str) -> str | None:
        # 1. Absolute.
        if resolver.slug_to_path(target_slug, wiki_root) is not None:
            return target_slug
        # 2. Sibling.
        if source_dir:
            candidate = f"{source_dir}/{target_slug}"
            if resolver.slug_to_path(candidate, wiki_root) is not None:
                return candidate
            # 3. Ancestor walk.
            parts = source_dir.split("/")
            for depth in range(len(parts) - 1, 0, -1):
                candidate = f"{'/'.join(parts[:depth])}/{target_slug}"
                if resolver.slug_to_path(candidate, wiki_root) is not None:
                    return candidate
        return None

    def replace(match: re.Match[str]) -> str:
        target_slug = match.group(1).strip()
        fragment = match.group(2)
        display = match.group(3) or target_slug
        resolved_slug = _resolve_target(target_slug)
        if resolved_slug is None:
            broken.append(target_slug)
            return f'<a class="memex-broken" href="#" title="broken wikilink">{display}</a>'
        url = resolver.slug_to_url(resolved_slug)
        if fragment:
            url = f"{url}#{fragment}"
        return f"[{display}]({url})"

    return WIKILINK_RE.sub(replace, markdown)


_LEADING_H1_RE = re.compile(r"\A\s*#\s+([^\n]+?)\s*\n", re.MULTILINE)


def _strip_leading_h1(body: str) -> tuple[str, str | None]:
    """Strip the body's leading ATX H1 and return `(stripped_body, h1_text)`.

    The page template always renders the page title as a chrome `<h1>`, so
    repeating the body's leading H1 below it produces an unsightly
    duplicate. We strip the body H1 unconditionally and promote its text
    into the title fallback chain in `render()` — pages without a
    frontmatter `title:` then still get a sensible page title from the
    body's first heading without rendering it twice.

    Setext H1s (using `===`) are intentionally left alone — they're rare
    enough in practice to not be worth the parser complexity.
    """
    match = _LEADING_H1_RE.match(body)
    if not match:
        return body, None
    return body[match.end() :], match.group(1).strip()


def render(content: str, source_slug: str, wiki_root: Path) -> RenderedPage:
    """Render markdown to a RenderedPage."""
    fm, body = frontmatter.split(content)
    fm = fm or {}
    broken: list[str] = []
    headings: list[tuple[int, str, str]] = []

    body, leading_h1 = _strip_leading_h1(body)
    body = _expand_wikilinks(body, source_slug, wiki_root, broken)

    md = mistune.create_markdown(
        renderer=_DocsiteRenderer(
            source_slug=source_slug,
            wiki_root=wiki_root,
            broken_links=broken,
            headings=headings,
        ),
        plugins=["strikethrough", "footnotes", "table", "url", "task_lists"],
    )
    html = md(body)

    title = (
        fm.get("title")
        or leading_h1
        or (headings[0][2] if headings else None)
        or source_slug.rsplit("/", 1)[-1].replace("-", " ").title()
    )

    # mistune's Markdown.__call__ is typed `str | list[dict[...]]` because it
    # supports a renderer-less mode. We always pass an HTMLRenderer so the
    # return is a string in practice.
    return RenderedPage(
        slug=source_slug,
        title=str(title),
        html=html if isinstance(html, str) else "",
        frontmatter=fm,
        headings=headings,
        broken_links=broken,
    )
