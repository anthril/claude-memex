"""Write helpers for `/open-questions` and `/rules` submissions.

Frontmatter is constructed from form input + the project's profile
requirements, then validated against the same rule set the
`frontmatter-check.py` PostToolUse hook applies. The docsite uses a
parity copy of the validator (in `memex_docsite/frontmatter.py`)
because the hook scripts aren't shipped in the installed Python
package — they ride the plugin repo. The two implementations are kept
in sync by `tests/test_docsite_frontmatter_parity.py`.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter
from .config import DocsiteConfig

OPEN_QUESTIONS_DIR = ".open-questions"
RESOLVED_DIR = ".resolved"
RULES_DIR = ".rules"

_SAFE_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class WriteResult:
    path: Path
    slug: str


def slugify(title: str, *, max_len: int = 60) -> str:
    """Turn a title into a kebab-case slug. Falls back to a date stamp on empty input."""
    slug = _SAFE_SLUG.sub("-", title.strip().casefold()).strip("-")
    if not slug:
        slug = _dt.datetime.now().strftime("untitled-%Y%m%d-%H%M%S")
    return slug[:max_len].strip("-") or "untitled"


def unique_slug(folder: Path, base_slug: str) -> str:
    """Append `-2`, `-3`, … to the slug until no `<slug>.md` exists in `folder`."""
    candidate = base_slug
    counter = 2
    while (folder / f"{candidate}.md").exists():
        candidate = f"{base_slug}-{counter}"
        counter += 1
    return candidate


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_frontmatter(
    *,
    cfg: DocsiteConfig,
    title: str,
    slug: str,
    type_value: str,
    extra: dict | None = None,
) -> dict:
    """Construct frontmatter satisfying the project's required fields."""
    required = (cfg.raw_config.get("frontmatter") or {}).get("required") or []
    fm: dict = {
        "title": title,
        "slug": slug,
        "type": type_value,
        "status": "draft",
        "created": _now_iso(),
        "updated": _now_iso(),
    }
    # Optional but commonly required.
    if "owner" in required:
        fm["owner"] = (extra or {}).get("owner") or "anonymous"
    if extra:
        for key, val in extra.items():
            if key not in fm and val is not None and val != "":
                fm[key] = val
    return fm


def _validate(content: str, cfg: DocsiteConfig) -> None:
    """Validate against the project's required fields + enums.

    Mirrors the `frontmatter-check.py` PostToolUse hook so writes the
    hook would reject can never come in via the browser.
    """
    fm_cfg = cfg.raw_config.get("frontmatter") or {}
    required = list(fm_cfg.get("required") or [])
    enums = fm_cfg.get("enum") or {}
    ok, message = frontmatter.validate(content, required, enums)
    if not ok:
        raise ValueError(f"frontmatter validation failed: {message}")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# ─── public API ────────────────────────────────────────────────────────────────


def submit_open_question(
    cfg: DocsiteConfig,
    *,
    title: str,
    body: str,
    author: str,
    owner: str | None = None,
    related: str | None = None,
) -> WriteResult:
    folder = _ensure_dir(cfg.wiki_root / OPEN_QUESTIONS_DIR)
    slug = unique_slug(folder, slugify(title))
    fm = _build_frontmatter(
        cfg=cfg,
        title=title,
        slug=slug,
        type_value="open-question",
        extra={"owner": owner or author, "author": author, "related": related},
    )
    content = frontmatter.serialize(fm, body.strip() + "\n")
    _validate(content, cfg)
    target = folder / f"{slug}.md"
    target.write_text(content, encoding="utf-8")
    return WriteResult(path=target, slug=slug)


def resolve_open_question(cfg: DocsiteConfig, slug: str, *, resolver: str) -> WriteResult:
    folder = cfg.wiki_root / OPEN_QUESTIONS_DIR
    src = folder / f"{slug}.md"
    if not src.is_file():
        raise FileNotFoundError(f"open question not found: {slug}")
    content = src.read_text(encoding="utf-8", errors="replace")
    fm, body = frontmatter.split(content)
    fm = fm or {}
    fm["status"] = "resolved"
    fm["resolved_at"] = _now_iso()
    fm["resolved_by"] = resolver
    fm["updated"] = _now_iso()
    new_content = frontmatter.serialize(fm, body)
    resolved_dir = _ensure_dir(folder / RESOLVED_DIR)
    target = resolved_dir / f"{slug}.md"
    counter = 2
    while target.exists():
        target = resolved_dir / f"{slug}-{counter}.md"
        counter += 1
    target.write_text(new_content, encoding="utf-8")
    src.unlink()
    return WriteResult(path=target, slug=slug)


def submit_rule(
    cfg: DocsiteConfig,
    *,
    title: str,
    body: str,
    author: str,
    owner: str | None = None,
    scope: str | None = None,
) -> WriteResult:
    folder = _ensure_dir(cfg.wiki_root / RULES_DIR)
    slug = unique_slug(folder, slugify(title))
    fm = _build_frontmatter(
        cfg=cfg,
        title=title,
        slug=slug,
        type_value="rule",
        extra={"owner": owner or author, "author": author, "scope": scope},
    )
    content = frontmatter.serialize(fm, body.strip() + "\n")
    _validate(content, cfg)
    target = folder / f"{slug}.md"
    target.write_text(content, encoding="utf-8")
    return WriteResult(path=target, slug=slug)


def list_open_questions(cfg: DocsiteConfig) -> list[dict]:
    """Return [{slug, title, status, created, body_preview, resolved}, ...]."""
    out = []
    folder = cfg.wiki_root / OPEN_QUESTIONS_DIR
    if folder.is_dir():
        for path in sorted(folder.glob("*.md")):
            out.append(_summarise(path, resolved=False, wiki_root=cfg.wiki_root))
    resolved_dir = folder / RESOLVED_DIR
    if resolved_dir.is_dir():
        for path in sorted(resolved_dir.glob("*.md")):
            out.append(_summarise(path, resolved=True, wiki_root=cfg.wiki_root))
    return out


def list_rules(cfg: DocsiteConfig) -> list[dict]:
    folder = cfg.wiki_root / RULES_DIR
    if not folder.is_dir():
        return []
    return [
        _summarise(path, resolved=False, wiki_root=cfg.wiki_root)
        for path in sorted(folder.glob("*.md"))
    ]


def _summarise(path: Path, *, resolved: bool, wiki_root: Path | None = None) -> dict:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"slug": path.stem, "title": path.stem, "resolved": resolved}
    fm, body = frontmatter.split(content)
    fm = fm or {}
    preview = body.strip().split("\n\n", 1)[0][:200].replace("\n", " ").strip()
    if wiki_root is not None:
        try:
            url = "/" + path.resolve().relative_to(wiki_root.resolve()).as_posix().removesuffix(".md")
        except ValueError:
            url = None
    else:
        url = None
    return {
        "slug": fm.get("slug") or path.stem,
        "title": fm.get("title") or path.stem,
        "status": fm.get("status", "draft"),
        "created": fm.get("created"),
        "owner": fm.get("owner"),
        "body_preview": preview,
        "resolved": resolved,
        "url": url,
        "path": str(path),
    }
