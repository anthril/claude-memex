"""_lib — shared helpers for every Memex hook script.

On import, force stderr to UTF-8 so hook messages containing unicode
(em-dashes, arrows, emoji) don't blow up on Windows consoles defaulting to
cp1252 / cp850. Claude Code reads stderr as UTF-8 regardless of platform.
"""
import contextlib as _contextlib
import sys as _sys

# Older Python on exotic platforms may lack TextIOBase.reconfigure — best-effort only
with _contextlib.suppress(Exception):
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
