"""First-party inline-annotation backend.

Each annotation is a regular markdown file under
`<wiki_root>/.annotations/<page-slug>/<id>.md`. Frontmatter encodes the
W3C Web Annotation Data Model selectors (TextQuoteSelector for
robustness across edits, plus TextPositionSelector as a fast first-pass
match), visibility, and threading metadata. Replies are sibling files
that set `replies_to: <parent-id>` in their frontmatter.

The folder layout means annotations are git-trackable, diffable, and
exportable like the rest of the wiki. Hooks ignore them by default
because `.annotations/` doesn't appear in any profile's `appliesTo`
glob — annotations are a docsite-internal artefact.
"""
from __future__ import annotations

import datetime as _dt
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from . import frontmatter, wiki_log
from .config import DocsiteConfig

ANNOTATIONS_DIR = ".annotations"
Visibility = Literal["public", "group", "private"]
VALID_VISIBILITIES: tuple[Visibility, ...] = ("public", "group", "private")

_SAFE_PAGE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True)
class AnnotationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _safe_page_slug(page_slug: str) -> str:
    """Sanitise a page slug into a path-safe folder name (per segment)."""
    parts = []
    for segment in page_slug.strip("/").split("/"):
        cleaned = _SAFE_PAGE_SEGMENT.sub("-", segment).strip("-")
        if not cleaned or cleaned in (".", ".."):
            raise AnnotationError(f"invalid page slug segment: {segment!r}")
        parts.append(cleaned)
    if not parts:
        raise AnnotationError("page slug is required")
    return "/".join(parts)


def annotation_dir(cfg: DocsiteConfig, page_slug: str) -> Path:
    return cfg.memex_root / ANNOTATIONS_DIR / _safe_page_slug(page_slug)


def _validate_selector(selector: dict | None) -> dict:
    """Make sure the W3C TextQuoteSelector payload is well-formed."""
    if not isinstance(selector, dict):
        raise AnnotationError("selector is required")
    sel_type = selector.get("type") or "TextQuoteSelector"
    if sel_type != "TextQuoteSelector":
        raise AnnotationError("selector.type must be 'TextQuoteSelector'")
    quote = selector.get("exact")
    if not isinstance(quote, str) or not quote.strip():
        raise AnnotationError("selector.exact must be a non-empty string")
    out: dict = {"type": "TextQuoteSelector", "exact": quote}
    if "prefix" in selector and isinstance(selector["prefix"], str):
        out["prefix"] = selector["prefix"]
    if "suffix" in selector and isinstance(selector["suffix"], str):
        out["suffix"] = selector["suffix"]
    return out


def _validate_position(position: dict | None) -> dict | None:
    if not position:
        return None
    if not isinstance(position, dict):
        raise AnnotationError("position must be a dict if provided")
    start = position.get("start")
    end = position.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
        raise AnnotationError("position.start/end must be non-negative ints with start <= end")
    return {"type": "TextPositionSelector", "start": start, "end": end}


def _validate_visibility(value: object | None, default: Visibility) -> Visibility:
    if value is None:
        return default
    if value in VALID_VISIBILITIES:
        return value
    raise AnnotationError(
        f"visibility must be one of {VALID_VISIBILITIES}, got {value!r}"
    )


@dataclass(slots=True)
class WriteResult:
    path: Path
    record: dict


# ─── public API ────────────────────────────────────────────────────────────────


def list_annotations(
    cfg: DocsiteConfig,
    page_slug: str,
    *,
    viewer_name: str,
    is_authenticated: bool,
) -> list[dict]:
    """Return annotations for a page, filtered by visibility for `viewer_name`."""
    folder = annotation_dir(cfg, page_slug)
    if not folder.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(folder.glob("*.md")):
        rec = _read(path)
        if rec is None:
            continue
        if not _can_view(rec, viewer_name=viewer_name, is_authenticated=is_authenticated):
            continue
        out.append(rec)
    out.sort(key=lambda r: r.get("created") or "")
    return out


def create_annotation(
    cfg: DocsiteConfig,
    page_slug: str,
    *,
    body: str,
    selector: dict,
    position: dict | None,
    author: str,
    visibility: Visibility | None = None,
    replies_to: str | None = None,
) -> WriteResult:
    safe_slug = _safe_page_slug(page_slug)
    folder = (cfg.memex_root / ANNOTATIONS_DIR / safe_slug)
    folder.mkdir(parents=True, exist_ok=True)
    if cfg.annotations.allow_anonymous is False and author == "anonymous":
        raise AnnotationError("anonymous annotations are disabled")

    sel = _validate_selector(selector)
    pos = _validate_position(position)
    vis = _validate_visibility(visibility, default=cfg.annotations.default_visibility)

    if replies_to is not None:
        parent_path = folder / f"{replies_to}.md"
        if not parent_path.is_file():
            raise AnnotationError(f"parent annotation not found: {replies_to}")

    ann_id = _new_id()
    title = f"Annotation on {safe_slug}" + (" (reply)" if replies_to else "")
    fm: dict = {
        "title": title,
        "slug": ann_id,
        "type": "annotation",
        "status": "active",
        "created": _now_iso(),
        "updated": _now_iso(),
        "author": author,
        "visibility": vis,
        "page": safe_slug,
        "selector": sel,
    }
    if pos is not None:
        fm["position"] = pos
    if replies_to is not None:
        fm["replies_to"] = replies_to

    body = (body or "").strip()
    if not body:
        raise AnnotationError("body is required")
    content = frontmatter.serialize(fm, body + "\n")

    target = folder / f"{ann_id}.md"
    target.write_text(content, encoding="utf-8")
    wiki_log.append_entry(
        cfg,
        event="annotation",
        subject=f"{safe_slug} (by {author})",
    )
    record = _summarise(target, fm)
    return WriteResult(path=target, record=record)


def update_annotation(
    cfg: DocsiteConfig,
    page_slug: str,
    ann_id: str,
    *,
    body: str | None,
    visibility: Visibility | None,
    author: str,
    is_authenticated: bool,
) -> WriteResult:
    target = annotation_dir(cfg, page_slug) / f"{ann_id}.md"
    if not target.is_file():
        raise AnnotationError(f"annotation not found: {ann_id}")
    existing = _read(target)
    if existing is None:
        raise AnnotationError(f"annotation file unreadable: {ann_id}")
    if not _can_edit(existing, author=author, is_authenticated=is_authenticated):
        raise AnnotationError("you can only edit your own annotations")

    fm = existing["frontmatter"]
    if body is not None:
        body = body.strip()
        if not body:
            raise AnnotationError("body is required")
    if visibility is not None:
        fm["visibility"] = _validate_visibility(visibility, default=fm.get("visibility", "public"))
    fm["updated"] = _now_iso()
    final_body = (body if body is not None else existing["body"]).rstrip() + "\n"
    target.write_text(frontmatter.serialize(fm, final_body), encoding="utf-8")
    return WriteResult(path=target, record=_summarise(target, fm))


def delete_annotation(
    cfg: DocsiteConfig,
    page_slug: str,
    ann_id: str,
    *,
    author: str,
    is_authenticated: bool,
) -> None:
    """Soft-delete: status flips to `deleted`, body is cleared."""
    target = annotation_dir(cfg, page_slug) / f"{ann_id}.md"
    if not target.is_file():
        raise AnnotationError(f"annotation not found: {ann_id}")
    existing = _read(target)
    if existing is None:
        return
    if not _can_edit(existing, author=author, is_authenticated=is_authenticated):
        raise AnnotationError("you can only delete your own annotations")
    fm = existing["frontmatter"]
    fm["status"] = "deleted"
    fm["updated"] = _now_iso()
    target.write_text(
        frontmatter.serialize(fm, "_(deleted)_\n"), encoding="utf-8"
    )


# ─── helpers ───────────────────────────────────────────────────────────────────


def _read(path: Path) -> dict | None:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fm, body = frontmatter.split(content)
    if fm is None:
        return None
    return {"frontmatter": fm, "body": body.strip(), **_summarise(path, fm)}


def _summarise(path: Path, fm: dict) -> dict:
    return {
        "id": fm.get("slug") or path.stem,
        "page": fm.get("page"),
        "author": fm.get("author") or "anonymous",
        "visibility": fm.get("visibility") or "public",
        "created": fm.get("created"),
        "updated": fm.get("updated"),
        "status": fm.get("status") or "active",
        "selector": fm.get("selector"),
        "position": fm.get("position"),
        "replies_to": fm.get("replies_to"),
        "body": _strip_body(path),
    }


def _strip_body(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    _, body = frontmatter.split(content)
    return body.strip()


def _can_view(rec: dict, *, viewer_name: str, is_authenticated: bool) -> bool:
    if rec.get("status") == "deleted":
        # Tombstones are visible to the author and to authenticated users in group/public.
        if rec.get("visibility") == "private":
            return rec.get("author") == viewer_name
        return is_authenticated or rec.get("visibility") == "public"
    vis = rec.get("visibility") or "public"
    if vis == "public":
        return True
    if vis == "group":
        return is_authenticated
    if vis == "private":
        return rec.get("author") == viewer_name
    return False


def _can_edit(rec: dict, *, author: str, is_authenticated: bool) -> bool:
    if rec.get("status") == "deleted":
        return False
    return rec.get("frontmatter", rec).get("author") == author
