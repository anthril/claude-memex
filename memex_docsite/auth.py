"""Auth middleware for write routes.

Three modes (set in `memex.config.json` -> `docsite.auth`):

- `none`   — no auth. Identity defaults to "anonymous" (or whatever the
             form supplies for `author`). Bind to 127.0.0.1 in the CLI.
- `token`  — accept a shared token via either:
                 Authorization: Bearer <token>
                 _memex_token   hidden form field
                 memex_token=…  cookie
             Token value comes from `MEMEX_DOCSITE_TOKEN` env var.
- `proxy`  — trust `X-Forwarded-User` set by an upstream reverse proxy
             (Tailscale, Cloudflare Access, etc.). The header value
             becomes the submission `author`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from starlette.exceptions import HTTPException
from starlette.requests import Request

from .config import DocsiteConfig

ENV_TOKEN = "MEMEX_DOCSITE_TOKEN"


@dataclass(slots=True)
class Identity:
    name: str
    is_anonymous: bool = False


def _expected_token() -> str | None:
    return os.environ.get(ENV_TOKEN) or None


def _bearer_from_header(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def _token_from_form(form: dict) -> str | None:
    val = form.get("_memex_token")
    return val.strip() if isinstance(val, str) and val.strip() else None


def _token_from_cookie(request: Request) -> str | None:
    val = request.cookies.get("memex_token")
    return val.strip() if val and val.strip() else None


def identify(request: Request, cfg: DocsiteConfig, *, form: dict | None = None) -> Identity:
    """Return the caller's identity given the configured auth mode.

    Read-only: callers that need to enforce auth on writes should use
    `require_write_identity(...)` instead.
    """
    if cfg.auth == "proxy":
        forwarded = request.headers.get("x-forwarded-user")
        if forwarded:
            return Identity(name=forwarded.strip(), is_anonymous=False)
        return Identity(name="anonymous", is_anonymous=True)

    if cfg.auth == "token":
        # Token presence promotes the caller from anonymous to authenticated.
        # The actual token check happens in `require_write_identity`.
        token = (
            _bearer_from_header(request)
            or (form and _token_from_form(form))
            or _token_from_cookie(request)
        )
        if token and token == _expected_token():
            return Identity(name=os.environ.get("MEMEX_DOCSITE_USER", "writer"), is_anonymous=False)
        return Identity(name="anonymous", is_anonymous=True)

    # auth == "none": always anonymous unless the form supplied an author.
    name = (form or {}).get("author") or "anonymous"
    return Identity(name=str(name).strip() or "anonymous", is_anonymous=name == "anonymous")


def require_write_identity(
    request: Request, cfg: DocsiteConfig, *, form: dict | None = None
) -> Identity:
    """Identity for a write request. Raises HTTPException(401) if auth fails."""
    if cfg.auth == "none":
        return identify(request, cfg, form=form)

    if cfg.auth == "proxy":
        forwarded = request.headers.get("x-forwarded-user")
        if not forwarded:
            raise HTTPException(401, "missing X-Forwarded-User header")
        return Identity(name=forwarded.strip(), is_anonymous=False)

    # token mode
    expected = _expected_token()
    if not expected:
        raise HTTPException(
            500,
            f"docsite.auth=token requires the {ENV_TOKEN} env var to be set",
        )
    presented = (
        _bearer_from_header(request)
        or (form and _token_from_form(form))
        or _token_from_cookie(request)
    )
    if not presented or presented != expected:
        raise HTTPException(401, "invalid or missing token")
    return Identity(name=os.environ.get("MEMEX_DOCSITE_USER", "writer"), is_anonymous=False)
