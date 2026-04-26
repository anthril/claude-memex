"""Sanity checks for Phase 6 packaging artefacts (Dockerfile, compose, .dockerignore).

These don't require Docker installed; they parse the files and assert
key directives are still present so accidental edits don't ship a
broken image. A real `docker build` is left for CI / release pipelines.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


def test_dockerfile_present_and_minimal_directives():
    assert DOCKERFILE.is_file()
    content = DOCKERFILE.read_text(encoding="utf-8")
    # Base image is the same Python series the package supports.
    assert "FROM python:3.12-slim" in content
    # Image must install the docsite extras (not just hooks).
    assert ".[docsite]" in content
    # Container must expose the port and run as non-root.
    assert "EXPOSE 8000" in content
    assert "USER memex" in content
    # Healthcheck is wired so orchestrators can detect liveness.
    assert "HEALTHCHECK" in content
    assert "/api/health" in content
    # Entry point uses the console-script the project exposes.
    assert "memex-docsite" in content


def test_compose_yaml_parses():
    pytest.importorskip("yaml")
    import yaml

    parsed = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    services = parsed.get("services") or {}
    assert "docsite" in services, "compose must define a `docsite` service"
    docsite = services["docsite"]
    # The default deployment runs the writeable token-mode CLI.
    cmd = docsite.get("command") or []
    assert "memex-docsite" in cmd
    assert "serve" in cmd
    assert "--auth" in cmd and "token" in cmd
    # Token must come from env so it isn't checked in.
    env = docsite.get("environment") or {}
    assert "MEMEX_DOCSITE_TOKEN" in env
    # Wiki path is supplied at runtime so the image stays generic.
    volumes = docsite.get("volumes") or []
    assert any("MEMEX_WIKI_PATH" in v and "/wiki" in v for v in volumes)
    # Port is exposed.
    ports = docsite.get("ports") or []
    assert any("8000:8000" in p for p in ports)


def test_dockerignore_keeps_secrets_and_caches_out():
    assert DOCKERIGNORE.is_file()
    rules = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    # Local virtualenvs and Python caches should never be baked in.
    assert ".venv" in rules
    assert "**/__pycache__" in rules
    # Local .env files (the compose ones) must not leak into the image.
    assert ".env" in rules
    assert ".env.*" in rules
    # Tests + examples bloat the image without runtime value.
    assert "tests" in rules
    assert "examples" in rules


def test_docs_docker_md_present():
    docs = REPO_ROOT / "docs" / "docker.md"
    assert docs.is_file()
    text = docs.read_text(encoding="utf-8")
    # The doc should at least cover token mode, proxy mode, and a healthcheck.
    assert "MEMEX_DOCSITE_TOKEN" in text
    assert "proxy" in text.lower()
    assert "/api/health" in text
