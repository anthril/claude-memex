"""Search backend for the docsite — grep over the wiki, optional qmd upgrade.

The retrieval logic is extracted from
`hooks/scripts/user-prompt-context.py` so the docsite and the
session-context hook agree on what 'relevant' means.

Default engine: stdlib grep (count term occurrences across all `.md`).
If `search.engine == "qmd"` in `memex.config.json` AND a `qmd` binary is
on PATH (or pointed at by `MEMEX_QMD_BIN`), we shell out to it for
BM25 + vector retrieval.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter, resolver

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "as", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "i", "you", "we", "they",
    "it", "this", "that", "these", "those", "my", "your", "our", "their",
    "can", "could", "should", "would", "will", "from", "into", "about",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "say", "says", "said", "tell", "tells", "told", "mean", "means",
    "there", "here",
}

WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-]{2,}")


@dataclass(slots=True)
class SearchResult:
    slug: str
    title: str
    snippet: str
    score: float
    path: Path


def _keywords(text: str, limit: int = 8) -> list[str]:
    words = WORD_RE.findall(text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS)
    return [w for w, _ in freq.most_common(limit)]


def _qmd_binary() -> str | None:
    override = os.environ.get("MEMEX_QMD_BIN")
    if override and Path(override).is_file():
        return override
    return shutil.which("qmd")


def _qmd_search(wiki_root: Path, query: str, top_n: int) -> list[tuple[str, float]] | None:
    qmd = _qmd_binary()
    if not qmd:
        return None
    try:
        proc = subprocess.run(
            [qmd, "query", "--json", "-n", str(top_n), "--", query],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(wiki_root),
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        candidates = parsed.get("results") or parsed.get("hits") or []
    elif isinstance(parsed, list):
        candidates = parsed
    else:
        return None

    out: list[tuple[str, float]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        path = item.get("file") or item.get("filepath") or item.get("path")
        if not path:
            continue
        if os.path.isabs(path):
            try:
                path = os.path.relpath(path, str(wiki_root))
            except ValueError:
                continue
        out.append((path.replace("\\", "/"), float(item.get("score") or 0.0)))
    return out[:top_n] or None


def _grep_search(
    wiki_root: Path,
    terms: list[str],
    top_n: int,
    *,
    show_hidden: bool,
    is_ignored=None,
) -> list[tuple[str, float]]:
    if not terms:
        return []
    scored: list[tuple[str, float]] = []
    for path in wiki_root.rglob("*.md"):
        rel = path.relative_to(wiki_root)
        if any(p == ".state" for p in rel.parts):
            continue
        if not show_hidden and any(p.startswith(".") for p in rel.parts):
            continue
        if is_ignored is not None and is_ignored(rel.as_posix()):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = content.lower()
        score = float(sum(low.count(t) for t in terms))
        if score > 0:
            scored.append((rel.as_posix(), score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def _build_snippet(content: str, terms: list[str], width: int = 240) -> str:
    """Pick a paragraph that contains the most query terms; trim around the first hit."""
    fm, body = frontmatter.split(content)
    body = body.strip()
    if not terms:
        return body[:width].replace("\n", " ").strip()
    low = body.lower()
    best_idx = -1
    best_score = -1
    for term in terms:
        idx = low.find(term)
        if idx == -1:
            continue
        # Score this hit by how many *other* terms appear within ±width.
        local = low[max(0, idx - width) : idx + width]
        s = sum(local.count(t) for t in terms)
        if s > best_score:
            best_score, best_idx = s, idx
    if best_idx == -1:
        return body[:width].replace("\n", " ").strip()
    start = max(0, best_idx - 60)
    end = min(len(body), best_idx + width)
    snippet = body[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "… " + snippet
    if end < len(body):
        snippet = snippet + " …"
    return snippet


def search(
    query: str,
    wiki_root: Path,
    *,
    top_n: int = 20,
    engine: str = "grep",
    show_hidden: bool = True,
    is_ignored=None,
) -> list[SearchResult]:
    """Run a search and return ranked results."""
    query = query.strip()
    if not query:
        return []

    pairs: list[tuple[str, float]] | None = None
    if engine == "qmd":
        pairs = _qmd_search(wiki_root, query, top_n)
    if not pairs:
        terms = _keywords(query)
        pairs = _grep_search(
            wiki_root, terms, top_n, show_hidden=show_hidden, is_ignored=is_ignored
        )
    else:
        terms = _keywords(query)

    results: list[SearchResult] = []
    for rel, score in pairs:
        path = (wiki_root / rel).resolve()
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, _ = frontmatter.split(content)
        fm = fm or {}
        slug = resolver.path_to_slug(path, wiki_root)
        title = (
            fm.get("title")
            or _first_heading(content)
            or slug.rsplit("/", 1)[-1].replace("-", " ").title()
        )
        results.append(
            SearchResult(
                slug=slug,
                title=str(title),
                snippet=_build_snippet(content, terms),
                score=score,
                path=path,
            )
        )
    return results


def _first_heading(content: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else None
