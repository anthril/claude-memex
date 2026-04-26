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
    """Convert `[[slug]]` and `[[slug|display]]` to standard `[display](url)`."""

    def replace(match: re.Match[str]) -> str:
        target_slug = match.group(1).strip()
        fragment = match.group(2)
        display = match.group(3) or target_slug
        path = resolver.slug_to_path(target_slug, wiki_root)
        if path is None:
            broken.append(target_slug)
            return f'<a class="memex-broken" href="#" title="broken wikilink">{display}</a>'
        url = resolver.slug_to_url(target_slug)
        if fragment:
            url = f"{url}#{fragment}"
        return f"[{display}]({url})"

    return WIKILINK_RE.sub(replace, markdown)


_LEADING_H1_RE = re.compile(r"\A\s*#\s+([^\n]+?)\s*\n", re.MULTILINE)


def _strip_leading_title_h1(body: str, fm_title: str | None) -> str:
    """If the body's first heading is a level-1 ATX heading whose text matches
    the frontmatter title, remove it. Avoids the duplicate-title rendering
    where `# AURORA` in the body shows up under a `<h1>{{ page.title }}</h1>`
    chrome that already exists in the page template.

    Conservative: only strips when frontmatter explicitly sets `title:` AND
    the body's first non-blank construct is an ATX H1. Setext H1s (===) and
    pages whose body H1 differs from the frontmatter title are left alone.
    """
    if not fm_title:
        return body
    match = _LEADING_H1_RE.match(body)
    if not match:
        return body
    body_h1_text = match.group(1).strip()
    if body_h1_text.casefold() == str(fm_title).strip().casefold():
        return body[match.end() :]
    return body


def render(content: str, source_slug: str, wiki_root: Path) -> RenderedPage:
    """Render markdown to a RenderedPage."""
    fm, body = frontmatter.split(content)
    fm = fm or {}
    broken: list[str] = []
    headings: list[tuple[int, str, str]] = []

    fm_title = fm.get("title")
    body = _strip_leading_title_h1(body, fm_title if isinstance(fm_title, str) else None)
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
