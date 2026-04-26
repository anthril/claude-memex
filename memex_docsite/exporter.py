"""Static export — crawl every renderable URL, write HTML files to a dist dir.

Phase 1 walks every `.md` under the wiki root, renders it, and writes the
output as `<slug>/index.html` (so URLs like `/foo/bar` work without a server).
Static assets are copied verbatim. Folder pages are auto-generated where no
`index.md` exists.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import graph as graph_module
from . import resolver
from .config import DocsiteConfig


@dataclass(slots=True)
class ExportResult:
    pages_written: int = 0
    folders_written: int = 0
    list_pages_written: int = 0
    assets_copied: int = 0
    broken_links: list[tuple[str, str]] = field(default_factory=list)
    """List of (slug, target) for every dead link encountered during render."""


def export(cfg: DocsiteConfig, *, out_dir: Path | None = None) -> ExportResult:
    """Render the entire wiki to a static directory."""
    # Imports done lazily so the exporter stays usable without all server deps.
    from . import sections as sections_module
    from . import server  # noqa: F401  (re-uses Jinja env via private helpers)
    from .server import (
        _comments_overview_response,
        _folder_response,
        _make_env,
        _open_questions_list_response,
        _page_response,
        _rules_list_response,
        _section_detail_response,
        _sections_overview_response,
    )

    static_cfg = _StaticDocsiteConfig.from_runtime(cfg)
    out = (out_dir or (cfg.project_root / cfg.export_path)).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Auto-protect against recursion: when `out` lives inside the wiki root
    # (a common shape when contentRoot=".") we'd walk our own freshly-written
    # output on the next pass. Wrap the project's `is_ignored` so anything
    # under `out` is also rejected, then mutate the cfg's ignore_patterns.
    out_resolved = out.resolve()
    wiki_resolved = cfg.wiki_root.resolve()
    try:
        out_rel = out_resolved.relative_to(wiki_resolved).as_posix()
        # Slug paths use POSIX separators; `<out_rel>/**` covers everything inside.
        extra = [out_rel, f"{out_rel}/**"]
        static_cfg.ignore_patterns = [*static_cfg.ignore_patterns, *extra]
    except ValueError:
        pass  # `out` lives outside the wiki — no recursion risk.

    env = _make_env()
    result = ExportResult()

    # Copy static/ verbatim.
    static_src = Path(__file__).parent / "static"
    static_dst = out / "static"
    shutil.copytree(static_src, static_dst)
    result.assets_copied = sum(1 for _ in static_dst.rglob("*") if _.is_file())

    # Build the graph once for the whole export so backlinks resolve consistently.
    graph = graph_module.build(
        cfg.wiki_root,
        show_hidden=static_cfg.show_hidden,
        is_ignored=static_cfg.is_ignored,
    )

    # Render every markdown file.
    for md_path in sorted(cfg.wiki_root.rglob("*.md")):
        rel = md_path.relative_to(cfg.wiki_root)
        if not static_cfg.show_hidden and any(p.startswith(".") for p in rel.parts):
            continue
        if static_cfg.is_ignored(rel.as_posix()):
            continue
        slug = resolver.path_to_slug(md_path, cfg.wiki_root)
        response = _page_response(static_cfg, env, slug, graph=graph)
        _write_html(out, slug, response.body)
        result.pages_written += 1

    # Auto-generated folder indexes (where no index.md exists).
    for folder in sorted(p for p in cfg.wiki_root.rglob("*") if p.is_dir()):
        rel = folder.relative_to(cfg.wiki_root)
        if not static_cfg.show_hidden and any(p.startswith(".") for p in rel.parts):
            continue
        if static_cfg.is_ignored(rel.as_posix()) or static_cfg.is_ignored(
            rel.as_posix() + "/"
        ):
            continue
        slug = "/".join(rel.parts)
        if not slug:
            continue
        if (folder / "index.md").is_file() or (folder / "README.md").is_file():
            continue
        response = _folder_response(static_cfg, env, slug, folder)
        _write_html(out, f"{slug}/index", response.body)
        result.folders_written += 1

    # Read-only list pages — open questions, rules, comments overview.
    # Submission forms are omitted from static output (they wouldn't work);
    # the helpers honour `static_mode` so the templates suppress write UIs.
    for slug, render in (
        ("open-questions", _open_questions_list_response),
        ("rules", _rules_list_response),
        ("comments", _comments_overview_response),
    ):
        response = render(static_cfg, env)
        _write_html(out, f"{slug}/index", response.body)
        result.list_pages_written += 1

    # Profile-driven sections nav. Skipped entirely when the profile
    # doesn't define `index.sections` or `frontmatter.enum.type`.
    if static_cfg.index_sections or static_cfg.type_enum:
        overview = _sections_overview_response(static_cfg, env, graph=graph)
        _write_html(out, "sections/index", overview.body)
        result.list_pages_written += 1
        for s in sections_module.build_sections(static_cfg, graph):
            detail = _section_detail_response(static_cfg, env, s.slug, graph=graph)
            _write_html(out, f"sections/{s.slug}/index", detail.body)
            result.list_pages_written += 1

    # Copy raw assets so /raw/<path> URLs continue to resolve.
    raw_src = cfg.wiki_root / "raw"
    if raw_src.is_dir():
        raw_dst = out / "raw"
        shutil.copytree(raw_src, raw_dst, dirs_exist_ok=True)

    return result


def _write_html(out: Path, slug: str, body: bytes) -> None:
    """Write the page so that the URL `slug_to_url(slug)` resolves to it on a static host."""
    if slug == "index":
        target = out / "index.html"
    elif slug.endswith("/index"):
        target = out / slug[: -len("index")] / "index.html"
    else:
        target = out / slug / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


class _StaticDocsiteConfig(DocsiteConfig):
    """A DocsiteConfig flavour that reports `static_mode = True` for the exporter."""

    @classmethod
    def from_runtime(cls, src: DocsiteConfig) -> _StaticDocsiteConfig:
        kwargs = {f: getattr(src, f) for f in src.__slots__}
        return cls(**kwargs)

    @property
    def static_mode(self) -> bool:
        return True
