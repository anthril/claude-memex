"""Tests for the auth layer (Phase 3)."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("starlette")
pytest.importorskip("yaml")

from starlette.exceptions import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402

from memex_docsite import auth  # noqa: E402
from memex_docsite import config as cfg_mod


def _make_request(headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode(), v.encode()))
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        raw_headers.append((b"cookie", cookie_header.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": raw_headers,
        "query_string": b"",
    }
    return Request(scope)


def test_none_mode_allows_anyone(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="none")
    request = _make_request()
    identity = auth.require_write_identity(request, cfg, form={"author": "Alice"})
    assert identity.name == "Alice"


def test_none_mode_defaults_to_anonymous(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="none")
    request = _make_request()
    identity = auth.require_write_identity(request, cfg, form={})
    assert identity.is_anonymous is True
    assert identity.name == "anonymous"


def test_token_mode_requires_env(research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(auth.ENV_TOKEN, raising=False)
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="token")
    request = _make_request()
    with pytest.raises(HTTPException) as exc:
        auth.require_write_identity(request, cfg, form={})
    assert exc.value.status_code == 500


def test_token_mode_accepts_bearer(research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(auth.ENV_TOKEN, "s3cret")
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="token")
    request = _make_request(headers={"Authorization": "Bearer s3cret"})
    identity = auth.require_write_identity(request, cfg, form={})
    assert identity.is_anonymous is False


def test_token_mode_rejects_wrong_token(research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(auth.ENV_TOKEN, "s3cret")
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="token")
    request = _make_request(headers={"Authorization": "Bearer wrong"})
    with pytest.raises(HTTPException) as exc:
        auth.require_write_identity(request, cfg, form={})
    assert exc.value.status_code == 401


def test_token_mode_accepts_form_field(research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(auth.ENV_TOKEN, "s3cret")
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="token")
    request = _make_request()
    identity = auth.require_write_identity(request, cfg, form={"_memex_token": "s3cret"})
    assert identity.is_anonymous is False


def test_token_mode_accepts_cookie(research_wiki_project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(auth.ENV_TOKEN, "s3cret")
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="token")
    request = _make_request(cookies={"memex_token": "s3cret"})
    identity = auth.require_write_identity(request, cfg, form={})
    assert identity.is_anonymous is False


def test_proxy_mode_uses_forwarded_user(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="proxy")
    request = _make_request(headers={"X-Forwarded-User": "alice@example.com"})
    identity = auth.require_write_identity(request, cfg, form={})
    assert identity.name == "alice@example.com"


def test_proxy_mode_rejects_missing_header(research_wiki_project: Path):
    cfg = cfg_mod.load(start=research_wiki_project)
    cfg = replace(cfg, auth="proxy")
    request = _make_request()
    with pytest.raises(HTTPException) as exc:
        auth.require_write_identity(request, cfg, form={})
    assert exc.value.status_code == 401
