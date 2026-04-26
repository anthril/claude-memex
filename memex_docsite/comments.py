"""Page-level comment threads — JSONL storage, append-mostly.

One file per page at `<wiki_root>/.comments/<safe-page-slug>.jsonl`.
Each line is a JSON record:

    {
      "id": "f3a1b2c3...",
      "author": "alice",
      "visibility": "public",      # public | group | private
      "created": "2026-04-26T15:42:00Z",
      "updated": null,             # ISO-8601 if edited
      "body": "the comment text",
      "replies_to": null,          # or another comment id
      "status": "active"           # active | deleted
    }

Append-mostly: new comments hit the end of the file. Edit/delete rewrite
the file with the modified record swapped in. Threading is client-side
via `replies_to`. Visibility filtering matches the annotation system.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from . import wiki_log
from .config import DocsiteConfig

COMMENTS_DIR = ".comments"
Visibility = Literal["public", "group", "private"]
VALID_VISIBILITIES: tuple[Visibility, ...] = ("public", "group", "private")

_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_BODY_LEN = 8000


@dataclass(slots=True)
class CommentError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _safe_slug(page_slug: str) -> str:
    parts = []
    for segment in page_slug.strip("/").split("/"):
        cleaned = _SAFE_SEGMENT.sub("-", segment).strip("-")
        if not cleaned or cleaned in (".", ".."):
            raise CommentError(f"invalid page slug segment: {segment!r}")
        parts.append(cleaned)
    if not parts:
        raise CommentError("page slug is required")
    return "/".join(parts)


def comments_path(cfg: DocsiteConfig, page_slug: str) -> Path:
    """Return the JSONL file backing a page's comment thread.

    Slashes in the slug are flattened to a single `__` separator so each
    page maps to exactly one file (no nested folders to walk).
    """
    safe = _safe_slug(page_slug)
    flat = safe.replace("/", "__")
    return cfg.memex_root / COMMENTS_DIR / f"{flat}.jsonl"


def _validate_visibility(value: object | None, default: Visibility) -> Visibility:
    if value is None:
        return default
    if value in VALID_VISIBILITIES:
        return value
    raise CommentError(
        f"visibility must be one of {VALID_VISIBILITIES}, got {value!r}"
    )


def _read_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    except OSError:
        return []
    return out


def _append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _rewrite_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _can_view(rec: dict, *, viewer_name: str, is_authenticated: bool) -> bool:
    vis = rec.get("visibility") or "public"
    if rec.get("status") == "deleted":
        return is_authenticated or rec.get("author") == viewer_name
    if vis == "public":
        return True
    if vis == "group":
        return is_authenticated
    if vis == "private":
        return rec.get("author") == viewer_name
    return False


# ─── public API ────────────────────────────────────────────────────────────────


def list_comments(
    cfg: DocsiteConfig,
    page_slug: str,
    *,
    viewer_name: str,
    is_authenticated: bool,
) -> list[dict]:
    """Return comments visible to `viewer_name`, ordered by `created` ascending."""
    path = comments_path(cfg, page_slug)
    records = _read_records(path)
    visible = [
        r for r in records
        if _can_view(r, viewer_name=viewer_name, is_authenticated=is_authenticated)
    ]
    visible.sort(key=lambda r: r.get("created") or "")
    return visible


def add_comment(
    cfg: DocsiteConfig,
    page_slug: str,
    *,
    body: str,
    author: str,
    visibility: Visibility | None = None,
    replies_to: str | None = None,
) -> dict:
    """Append a new comment. Returns the persisted record."""
    body = (body or "").strip()
    if not body:
        raise CommentError("body is required")
    if len(body) > _MAX_BODY_LEN:
        raise CommentError(f"body exceeds {_MAX_BODY_LEN} chars")

    path = comments_path(cfg, page_slug)
    records = _read_records(path)
    if replies_to is not None and not any(r.get("id") == replies_to for r in records):
        raise CommentError(f"parent comment not found: {replies_to}")

    vis = _validate_visibility(visibility, default="public")

    record = {
        "id": _new_id(),
        "author": author,
        "visibility": vis,
        "created": _now_iso(),
        "updated": None,
        "body": body,
        "replies_to": replies_to,
        "status": "active",
    }
    _append_record(path, record)
    wiki_log.append_entry(
        cfg,
        event="comment",
        subject=f"{page_slug} (by {author})",
    )
    return record


def update_comment(
    cfg: DocsiteConfig,
    page_slug: str,
    comment_id: str,
    *,
    body: str | None,
    visibility: Visibility | None,
    author: str,
) -> dict:
    path = comments_path(cfg, page_slug)
    records = _read_records(path)
    for rec in records:
        if rec.get("id") == comment_id:
            target = rec
            break
    else:
        raise CommentError(f"comment not found: {comment_id}")

    if target.get("author") != author:
        raise CommentError("you can only edit your own comments")
    if target.get("status") == "deleted":
        raise CommentError("cannot edit a deleted comment")

    if body is not None:
        body = body.strip()
        if not body:
            raise CommentError("body is required")
        if len(body) > _MAX_BODY_LEN:
            raise CommentError(f"body exceeds {_MAX_BODY_LEN} chars")
        target["body"] = body
    if visibility is not None:
        target["visibility"] = _validate_visibility(visibility, default=target.get("visibility", "public"))
    target["updated"] = _now_iso()

    _rewrite_records(path, records)
    return target


def list_recent_across_pages(
    cfg: DocsiteConfig,
    *,
    viewer_name: str,
    is_authenticated: bool,
    limit: int = 50,
) -> list[dict]:
    """Walk every page's JSONL file and return the most recent comments.

    Each returned record is augmented with `page` (the un-flattened page
    slug) and a stable `url` to the page itself.
    """
    folder = cfg.memex_root / COMMENTS_DIR
    if not folder.is_dir():
        return []
    out: list[dict] = []
    for path in folder.glob("*.jsonl"):
        page_slug = path.stem.replace("__", "/")
        for rec in _read_records(path):
            if not _can_view(rec, viewer_name=viewer_name, is_authenticated=is_authenticated):
                continue
            out.append(
                {
                    **rec,
                    "page": page_slug,
                    "url": "/" + page_slug if page_slug != "index" else "/",
                }
            )
    out.sort(key=lambda r: r.get("created") or "", reverse=True)
    return out[:limit]


def delete_comment(
    cfg: DocsiteConfig,
    page_slug: str,
    comment_id: str,
    *,
    author: str,
) -> None:
    """Soft-delete: status flips to `deleted`, body cleared."""
    path = comments_path(cfg, page_slug)
    records = _read_records(path)
    for rec in records:
        if rec.get("id") == comment_id:
            target = rec
            break
    else:
        raise CommentError(f"comment not found: {comment_id}")

    if target.get("author") != author:
        raise CommentError("you can only delete your own comments")
    target["status"] = "deleted"
    target["body"] = "_(deleted)_"
    target["updated"] = _now_iso()
    _rewrite_records(path, records)
