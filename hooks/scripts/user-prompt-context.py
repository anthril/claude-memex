#!/usr/bin/env python3
"""user-prompt-context.py — UserPromptSubmit hook

Retrieval over the wiki for each user prompt. Returns the top-N most relevant
pages as `additionalContext`.

Default engine is grep (stdlib, no deps). If `search.engine` is set to `qmd`
in memex.config.json AND a `qmd` binary is on PATH, we call:

    qmd query --json -n <max_pages> -- "<prompt>"

from the ops root. The JSON output is parsed; unexpected / non-zero exit →
graceful fallback to grep.

Override the binary path via the `MEMEX_QMD_BIN` environment variable (useful
for testing with a mock).
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib.config import load_config_from
from _lib.paths import find_project_root

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "as", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "i", "you", "we", "they",
    "it", "this", "that", "these", "those", "my", "your", "our", "their",
    "can", "could", "should", "would", "will", "from", "into", "about",
    # Question-word fillers — shouldn't drive retrieval scoring
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "say", "says", "said", "tell", "tells", "told", "mean", "means",
    "there", "here",
}

WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-]{2,}")


def keywords(text: str, limit: int = 8):
    words = WORD_RE.findall(text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS)
    return [w for w, _ in freq.most_common(limit)]


def grep_pages(ops_root: str, terms, max_pages: int):
    scores = []
    for root, _dirs, files in os.walk(ops_root):
        if "/.state" in root.replace("\\", "/"):
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, encoding="utf-8") as fh:
                    content = fh.read()
            except Exception:
                continue
            low = content.lower()
            score = 0
            for t in terms:
                score += low.count(t)
            if score > 0:
                rel = os.path.relpath(fp, ops_root).replace("\\", "/")
                scores.append((score, rel, content))
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:max_pages]


def first_heading_or_title(content: str) -> str:
    m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def first_summary_line(content: str) -> str:
    lines = content.splitlines()
    in_fm = False
    for line in lines:
        s = line.strip()
        if s == "---":
            in_fm = not in_fm
            continue
        if in_fm or not s or s.startswith("#"):
            continue
        return s[:200]
    return ""


def qmd_binary() -> str:
    """Resolve the qmd binary via env override or PATH."""
    override = os.environ.get("MEMEX_QMD_BIN")
    if override and os.path.isfile(override):
        return override
    found = shutil.which("qmd")
    return found or ""


def qmd_search(ops_root: str, prompt: str, max_pages: int):
    """Call qmd; return a list of (rel_path, score) or None on failure."""
    qmd = qmd_binary()
    if not qmd:
        return None
    try:
        r = subprocess.run(
            [qmd, "query", "--json", "-n", str(max_pages), "--", prompt],
            capture_output=True, text=True, timeout=5, cwd=ops_root,
            encoding="utf-8", errors="replace",
        )
    except Exception:
        return None

    if r.returncode != 0 or not r.stdout.strip():
        return None

    # qmd --json emits either a top-level list of results or an object like
    # {"results": [...]}. Handle both; each result is expected to carry at
    # least a `file`, `path`, or `filepath` field.
    try:
        parsed = json.loads(r.stdout)
    except Exception:
        return None

    if isinstance(parsed, dict):
        candidates = parsed.get("results") or parsed.get("hits") or []
    elif isinstance(parsed, list):
        candidates = parsed
    else:
        return None

    out = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        path = item.get("file") or item.get("filepath") or item.get("path")
        if not path:
            continue
        # Normalise to a rel path under ops_root if it's absolute
        if os.path.isabs(path):
            with contextlib.suppress(ValueError):
                path = os.path.relpath(path, ops_root)
        path = path.replace("\\", "/")
        score = item.get("score", 0)
        out.append((path, score))
    return out[:max_pages] if out else None


def format_line(ops_root_display: str, rel: str, content: str) -> str:
    title = first_heading_or_title(content) or "(untitled)"
    summary = first_summary_line(content)
    suffix = f": {summary}" if summary else ""
    return f"- **{ops_root_display}/{rel}** — {title}{suffix}"


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = payload.get("prompt") or payload.get("userPrompt") or ""
    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not prompt.strip():
        sys.exit(0)

    project_root = find_project_root(cwd)
    if not project_root:
        sys.exit(0)
    cfg = load_config_from(project_root)
    if not cfg:
        sys.exit(0)

    search_cfg = cfg.get("search") or {}
    max_pages = int(search_cfg.get("maxContextPages", 3))
    engine = search_cfg.get("engine", "grep")
    ops_root = os.path.join(project_root, cfg["root"])
    ops_display = cfg["root"]

    ctx_lines = []

    if engine == "qmd":
        results = qmd_search(ops_root, prompt, max_pages)
        if results:
            for rel, _score in results:
                fp = os.path.join(ops_root, rel)
                try:
                    with open(fp, encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue
                ctx_lines.append(format_line(ops_display, rel, content))

    if not ctx_lines:
        terms = keywords(prompt)
        if not terms:
            sys.exit(0)
        for _score, rel, content in grep_pages(ops_root, terms, max_pages):
            ctx_lines.append(format_line(ops_display, rel, content))

    if not ctx_lines:
        sys.exit(0)

    ctx = "### Relevant Memex pages\n\n" + "\n".join(ctx_lines)
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
