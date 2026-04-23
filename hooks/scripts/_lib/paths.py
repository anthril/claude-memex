"""Path helpers shared by every Memex hook script.

Conventions:
- All path operations run on a normalised forward-slash form
- "ops root" = the `.memex` directory inside the project; the `root` key in
  `memex.config.json` may rename it, so we always derive it from config
- "project root" = the directory containing `memex.config.json` (or `.memex/`)

Kebab-case:
- **ASCII default** (historical): `^[a-z0-9]+(-[a-z0-9]+)*$`
- **Unicode-friendly** (opt-in): any lowercase letter from any Unicode script
  plus digits, separated by ASCII hyphens. Enabled via the `asciiOnly: false`
  flag in `memex.config.json#/naming`. This is the recommended setting for
  non-English wikis (Japanese, Greek, Cyrillic, Arabic, etc.).
"""
from __future__ import annotations

import os
import re
import unicodedata

ASCII_KEBAB_SEGMENT_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ASCII_KEBAB_FILE_RE = re.compile(r"^(\d{2}-)?[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+$")
DATED_FOLDER_RE = re.compile(r"^\d{8}-\d{4}$")

# For Unicode: ASCII hyphen, ASCII digit, or a Unicode letter whose case is
# lowercase or has no case distinction at all (CJK, Hebrew, Arabic, etc.).
# `-`, `0-9`, `.` (in filenames) are always allowed.


def normalise(path: str) -> str:
    """Convert backslashes to forward slashes for portable matching."""
    return path.replace("\\", "/")


def find_project_root(start: str) -> str | None:
    """Walk up from `start` until a `memex.config.json` or `.memex/` dir is found.

    Returns the directory containing it, or None if nothing is found before
    the filesystem root.
    """
    cur = os.path.abspath(start)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    while True:
        if os.path.isfile(os.path.join(cur, "memex.config.json")):
            return cur
        if os.path.isdir(os.path.join(cur, ".memex")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def find_ops_root(project_root: str, config_root: str) -> str:
    """Resolve the absolute path of the `.memex/` equivalent under the project."""
    if os.path.isabs(config_root):
        return os.path.normpath(config_root)
    return os.path.normpath(os.path.join(project_root, config_root))


def rel_to_ops(file_path_norm: str, ops_root_norm: str) -> str | None:
    """Return the path relative to ops root, or None if outside it."""
    marker = "/" + ops_root_norm.rstrip("/").split("/")[-1] + "/"
    idx = file_path_norm.rfind(marker)
    if idx == -1:
        return None
    return file_path_norm[idx + len(marker):]


def inside_ops(file_path_norm: str, ops_root_norm: str) -> bool:
    """True if the file path lies under the ops root."""
    target = file_path_norm.rstrip("/")
    root = ops_root_norm.rstrip("/")
    return target == root or target.startswith(root + "/")


def _is_acceptable_letter(ch: str) -> bool:
    """True for any Unicode letter that is lowercase or caseless.

    Accepted Unicode categories:
    - `Ll` — lowercase letter (Latin lowercase, Greek/Cyrillic lowercase)
    - `Lo` — letter, other (Japanese, Chinese, Korean, Arabic, Hebrew — no case)
    - `Lm` — modifier letter (used as letters in some scripts)
    - `Mn` — nonspacing mark (Thai/Hindi/Arabic vowel signs; Vietnamese tones)
    - `Mc` — spacing mark (Devanagari vowel signs)

    Rejected:
    - ASCII `A-Z` and any Unicode `Lu` (uppercase), `Lt` (titlecase)
    - Numbers (handled separately), punctuation, symbols, separators, controls
    """
    if "a" <= ch <= "z":
        return True
    if "A" <= ch <= "Z":
        return False
    cat = unicodedata.category(ch)
    return cat in ("Ll", "Lo", "Lm", "Mn", "Mc")


def _is_acceptable_kebab_char(ch: str, unicode_ok: bool) -> bool:
    if "0" <= ch <= "9":
        return True
    if unicode_ok:
        return _is_acceptable_letter(ch)
    return "a" <= ch <= "z"


def is_kebab_segment(seg: str, *, unicode_ok: bool = False) -> bool:
    """A single folder name is valid kebab-case.

    ASCII mode (default): matches `^[a-z0-9]+(-[a-z0-9]+)*$`.
    Unicode mode: same structure, but letters may be any Unicode lowercase /
    caseless letter (Ll or Lo). Hyphens still ASCII.
    """
    if not seg:
        return False
    if not unicode_ok:
        return bool(ASCII_KEBAB_SEGMENT_RE.match(seg))
    # Unicode-friendly structural check:
    # 1. No leading or trailing hyphen
    # 2. No consecutive hyphens
    # 3. Every non-hyphen char is an acceptable kebab char
    if seg.startswith("-") or seg.endswith("-"):
        return False
    if "--" in seg:
        return False
    for ch in seg:
        if ch == "-":
            continue
        if not _is_acceptable_kebab_char(ch, unicode_ok=True):
            return False
    return True


def is_kebab_filename(fname: str, *, unicode_ok: bool = False) -> bool:
    """A filename with optional `NN-` ordering prefix + kebab stem + extension.

    ASCII mode (default): matches `^(\\d{2}-)?[a-z0-9]+(-[a-z0-9]+)*\\.[a-z0-9]+$`.
    Unicode mode: the stem follows Unicode kebab rules; the extension must
    still be ASCII lowercase+digits (file-system portability).
    """
    if not fname:
        return False
    if not unicode_ok:
        return bool(ASCII_KEBAB_FILE_RE.match(fname))
    # Split out the extension
    if "." not in fname:
        return False
    stem, ext = fname.rsplit(".", 1)
    if not re.match(r"^[a-z0-9]+$", ext):
        return False  # extensions stay ASCII for portability
    # Strip optional two-digit ordering prefix
    m = re.match(r"^(\d{2})-(.+)$", stem)
    if m:
        stem = m.group(2)
    return is_kebab_segment(stem, unicode_ok=True)


def is_dated_folder(seg: str) -> bool:
    return bool(DATED_FOLDER_RE.match(seg))
