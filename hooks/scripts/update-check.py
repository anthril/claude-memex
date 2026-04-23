#!/usr/bin/env python3
"""update-check.py — SessionStart hook

Optionally checks GitHub for a newer Memex release and surfaces a notice as
`additionalContext`. Skipped entirely unless the project's config opts in
via `hookEvents.sessionStart.updateCheck: true`.

Design goals:
- **Silent by default.** Opt-in only. Installed plugins in offline projects
  never touch the network.
- **Cheap.** Caches the result for 24h under `.memex/.state/update-check.json`
  so subsequent SessionStart calls hit the cache, not the API.
- **Fail closed.** Any network / parse / timeout error → silent exit. We
  never block a session on a connectivity issue.
- **Respects a release URL override.** `updateCheckUrl` in config can point
  at a mirror (for locked-down corp environments).

The URL polled: https://api.github.com/repos/anthril/claude-memex/releases/latest

Env override for testing: `MEMEX_UPDATE_CHECK_JSON` (file path; if set, the
hook reads release metadata from that file instead of fetching).
"""
from __future__ import annotations

import datetime
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root
from _lib.version import CURRENT_VERSION, is_newer

DEFAULT_RELEASE_URL = "https://api.github.com/repos/anthril/claude-memex/releases/latest"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CHECK_TIMEOUT_SECONDS = 3


def read_cache(cache_path: str):
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_cache(cache_path: str, data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass  # cache-write failure is not a blocker


def fetch_latest_release(url: str) -> dict | None:
    """Return {'tag_name': ..., 'html_url': ...} or None on any failure."""
    # Fixture override for tests
    fixture = os.environ.get("MEMEX_UPDATE_CHECK_JSON")
    if fixture and os.path.isfile(fixture):
        try:
            with open(fixture, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
    else:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "memex-update-check"})
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SECONDS, context=ctx) as r:
                if r.status != 200:
                    return None
                data = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, json.JSONDecodeError, OSError):
            return None

    if not isinstance(data, dict):
        return None
    return {
        "tag_name": data.get("tag_name") or "",
        "html_url": data.get("html_url") or "",
    }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project_root = find_project_root(cwd)
    if not project_root:
        sys.exit(0)
    cfg = load_config_from(project_root)
    if not cfg:
        sys.exit(0)

    opts = (cfg.get("hookEvents") or {}).get("sessionStart") or {}
    if not opts.get("updateCheck"):
        sys.exit(0)

    url = cfg.get("updateCheckUrl") or DEFAULT_RELEASE_URL
    cache_path = os.path.join(project_root, cfg["root"], ".state", "update-check.json")

    cache = read_cache(cache_path) or {}
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    cached_ts = cache.get("checked_at", 0)
    cached_latest = cache.get("latest_version", "")
    cached_url = cache.get("latest_url", "")

    if now - cached_ts < CACHE_TTL_SECONDS and cached_latest:
        latest_version = cached_latest
        latest_url = cached_url
    else:
        release = fetch_latest_release(url)
        if not release:
            sys.exit(0)
        latest_version = release["tag_name"].lstrip("v")
        latest_url = release["html_url"]
        write_cache(cache_path, {
            "checked_at": now,
            "latest_version": latest_version,
            "latest_url": latest_url,
            "current_version": CURRENT_VERSION,
        })

    if not latest_version:
        sys.exit(0)

    if not is_newer(latest_version, CURRENT_VERSION):
        sys.exit(0)

    ctx = (
        f"### Memex update available\n\n"
        f"- Installed: `{CURRENT_VERSION}`\n"
        f"- Latest: `{latest_version}`"
        + (f" — {latest_url}" if latest_url else "")
        + "\n\n"
        "Run `/plugin update claude-memex` to upgrade, or disable this check via "
        "`hookEvents.sessionStart.updateCheck: false` in `memex.config.json`."
    )
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
