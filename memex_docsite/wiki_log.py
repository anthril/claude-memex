"""Append entries to the wiki's `log.md` from browser-driven writes.

Hooks normally maintain `log.md` on Claude's tool calls (Stop hook —
`stop-log-append.py`), but writes via the docsite UI bypass that bus.
This module gives the submissions / comments / annotations writers a
small helper that appends a structured line using the project's
`log.entryPrefix` template, so a docsite-driven submission still shows
up in the next session's SessionStart context injection.

Best-effort — if the log file can't be written (permissions, missing
directory, locked file on Windows) the failure is swallowed; the
underlying write succeeded and surfacing a log error to the browser
would be confusing.
"""
from __future__ import annotations

import datetime as _dt
import os

from .config import DocsiteConfig

DEFAULT_PREFIX = "## [{date}] {event} | {subject}"


def _date_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def append_entry(
    cfg: DocsiteConfig,
    *,
    event: str,
    subject: str,
    body: str | None = None,
) -> None:
    """Append a single log entry. Format is driven by `log.entryPrefix` from
    `memex.config.json`; defaults to `## [{date}] {event} | {subject}`."""
    log_cfg = (cfg.raw_config.get("log") or {}) if cfg.raw_config else {}
    rel_path = str(log_cfg.get("path") or "log.md")
    prefix_tmpl = str(log_cfg.get("entryPrefix") or DEFAULT_PREFIX)

    target = (cfg.memex_root / rel_path).resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    try:
        header = prefix_tmpl.format(
            date=_date_now(), event=event, subject=subject
        )
    except (KeyError, IndexError):
        # User config has unsupported placeholders — fall back to default.
        header = DEFAULT_PREFIX.format(
            date=_date_now(), event=event, subject=subject
        )

    line = f"\n{header}\n"
    if body:
        line += body.rstrip() + "\n"

    try:
        # O_APPEND keeps writes atomic relative to other appenders on POSIX.
        # On Windows, the runtime serialises this for us — good enough for
        # the docsite's low write rate.
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(target, flags, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        # Best-effort; the actual data write already succeeded.
        return
