#!/usr/bin/env python3
"""migrate_from_operations.py — Lumioh `.operations/` → Memex `.memex/`

Mechanical migration helper invoked by the `/memex:migrate-from-operations`
slash command. Handles:

  1. Sanity-check the source `.operations/` tree
  2. Move `.operations/` → `.memex/` (git mv if in a git repo, else os.rename)
  3. Extract a matching `memex.config.json`
  4. Update in-tree references (`grep .operations/ → .memex/`) — dry-run diff only
  5. Append `log.md`

Use --dry-run to preview. Outputs JSON on stdout summarising the plan / actions.

The script is deliberately conservative: it refuses to overwrite `.memex/`, it
surfaces (but does not apply) in-tree string-replace edits, and it never
deletes source files unless `--delete-hooks` is passed explicitly.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

# Defaults derived from Lumioh's shipped `.operations/` taxonomy.
DEFAULT_ALLOWED_TOP_LEVEL = [
    "README.md",
    "AGENTS.md",
    "index.md",
    "log.md",
    ".audits",
    ".research",
    ".open-questions",
    ".rules",
    ".state",
    "entities",
    "platform",
    "workers",
    "workflows",
    "agents",
]

DEFAULT_README_REQUIRED = [
    "entities/*",
    "platform/features/*",
    "platform/systems/*",
    "workers/*",
    "agents/*",
    "workflows/*",
]

DEFAULT_FRONTMATTER_ENUM_TYPE = [
    "feature", "system", "entity", "worker", "agent", "workflow",
    "open-question", "rule",
]


def log(msg: str, *, stream=sys.stderr) -> None:
    stream.write(f"[migrate] {msg}\n")


def is_git_repo(path: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def infer_code_to_doc_mappings(project_root: Path) -> list[dict]:
    """Look at Lumioh-shaped source layouts and propose mappings.

    This is best-effort: we check for known directory shapes (Next.js App Router
    features, Supabase functions, Supabase migrations) and emit the mappings
    that Lumioh's hooks hard-coded.
    """
    mappings: list[dict] = []

    # Next.js App Router — (dashboard) group
    dashboard = project_root / "src" / "app" / "(console)" / "console" / "(dashboard)"
    if dashboard.exists():
        mappings.append({
            "codePattern": "src/app/(console)/console/(dashboard)/*/",
            "requiresDoc": "platform/features/{1}/README.md",
            "severity": "warn-then-block",
            "stateKey": "feature",
        })

    # Supabase edge functions
    if (project_root / "supabase" / "functions").exists():
        mappings.append({
            "codePattern": "supabase/functions/*/",
            "requiresDoc": "platform/systems/{1}/README.md OR platform/features/*/README.md (referencing)",
            "severity": "warn-then-block",
            "stateKey": "system",
        })

    # Supabase migrations
    if (project_root / "supabase" / "migrations").exists():
        mappings.append({
            "codePattern": "supabase/migrations/*.sql",
            "requiresDoc": "ANY .md containing the slug OR `-- Doc: .memex/<path>.md`",
            "severity": "block",
        })

    return mappings


def build_config(project_root: Path) -> dict:
    return {
        "$schema": "https://raw.githubusercontent.com/anthril/claude-memex/main/schemas/memex.config.schema.json",
        "version": "1",
        "profile": "engineering-ops",
        "root": ".memex",
        "allowedTopLevel": DEFAULT_ALLOWED_TOP_LEVEL,
        "datedFolders": {
            "paths": [".audits", ".research"],
            "format": "DDMMYYYY-HHMM",
        },
        "readmeRequired": DEFAULT_README_REQUIRED,
        "frontmatter": {
            "appliesTo": ["**/README.md", "**/AGENTS.md"],
            "required": ["title", "slug", "type", "status", "owner", "created", "updated"],
            "enum": {
                "type": DEFAULT_FRONTMATTER_ENUM_TYPE,
                "status": ["draft", "active", "deprecated"],
            },
        },
        "naming": {
            "exceptions": ["README.md", "AGENTS.md", "CHANGELOG.md", "CONVENTIONS.md", ".resolved"],
        },
        "codeToDocMapping": infer_code_to_doc_mappings(project_root),
        "log": {
            "path": "log.md",
            "entryPrefix": "## [{date}] {event} | {subject}",
        },
        "index": {
            "path": "index.md",
            "sections": [
                "Entities", "Features", "Systems", "Workers",
                "Workflows", "Open Questions", "Recent Activity",
            ],
        },
        "search": {"engine": "grep", "maxContextPages": 3},
    }


def find_reference_hits(project_root: Path) -> list[tuple[Path, int, str]]:
    """Walk the project looking for text-file references to `.operations/` that
    would need updating post-rename.

    Returns (path, line_number, line_content) tuples.
    """
    hits: list[tuple[Path, int, str]] = []
    exclude_dirs = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".operations", ".memex"}
    text_exts = {".md", ".ts", ".tsx", ".js", ".jsx", ".py", ".sql", ".json", ".yaml", ".yml", ".toml"}
    for root, dirs, files in os.walk(project_root):
        # In-place prune
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if Path(f).suffix.lower() not in text_exts:
                continue
            fp = Path(root) / f
            try:
                with open(fp, encoding="utf-8", errors="replace") as fh:
                    for lineno, line in enumerate(fh, 1):
                        if ".operations/" in line or ".operations\\" in line:
                            hits.append((fp, lineno, line.rstrip()))
            except Exception:
                continue
    return hits


def append_log(log_path: Path) -> None:
    date = datetime.date.today().isoformat()
    # ASCII arrow — log entries are consumed by grep / pagers on various encodings
    entry = f"\n## [{date}] migrate | .operations/ -> .memex/\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        log(f"failed to append log: {e}")


def plan(project_root: Path) -> dict:
    """Build an action plan without modifying anything."""
    ops = project_root / ".operations"
    memex = project_root / ".memex"
    config_path = project_root / "memex.config.json"
    out: dict = {"ok": False, "actions": [], "warnings": [], "errors": []}

    if not ops.exists():
        out["errors"].append(f"No .operations/ directory at {project_root}")
        return out
    if memex.exists():
        out["errors"].append(f".memex/ already exists at {project_root} — refusing to overwrite")
        return out
    if config_path.exists():
        out["warnings"].append("memex.config.json already exists — will be left alone")

    # Sanity-check the .operations/ shape
    for expected in ("AGENTS.md", "README.md"):
        if not (ops / expected).exists():
            out["warnings"].append(f".operations/{expected} not found — unusual shape")

    git_mode = is_git_repo(project_root)
    out["actions"].append({
        "kind": "move",
        "from": str(ops.relative_to(project_root)),
        "to": str(memex.name),
        "method": "git mv" if git_mode else "os.rename",
    })
    if not config_path.exists():
        cfg = build_config(project_root)
        out["actions"].append({
            "kind": "create",
            "path": config_path.name,
            "preview": {
                "allowedTopLevel": cfg["allowedTopLevel"][:3] + ["..."],
                "codeToDocMapping_count": len(cfg["codeToDocMapping"]),
            },
        })

    # Reference hits
    hits = find_reference_hits(project_root)
    if hits:
        out["warnings"].append(
            f"{len(hits)} in-tree references to `.operations/` will need updating after rename. "
            f"Review the 'reference_hits' list; apply the rewrites yourself."
        )
        out["reference_hits"] = [
            {"path": str(p.relative_to(project_root)).replace("\\", "/"), "line": n, "text": t}
            for p, n, t in hits[:200]
        ]

    out["actions"].append({"kind": "log-append", "path": ".memex/log.md"})

    out["ok"] = not out["errors"]
    return out


def execute(project_root: Path, dry_run: bool) -> dict:
    p = plan(project_root)
    if not p["ok"] or dry_run:
        p["executed"] = False
        return p

    ops = project_root / ".operations"
    memex = project_root / ".memex"

    # Move the tree
    if is_git_repo(project_root):
        r = subprocess.run(
            ["git", "-C", str(project_root), "mv", ".operations", ".memex"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            # Fall back to a filesystem rename
            log(f"git mv failed: {r.stderr.strip()} — falling back to os.rename")
            os.rename(ops, memex)
    else:
        os.rename(ops, memex)

    # Write the config
    config_path = project_root / "memex.config.json"
    if not config_path.exists():
        cfg = build_config(project_root)
        config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    # Append log
    append_log(memex / "log.md")

    p["executed"] = True
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", default=".", help="Project root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true", help="Preview without changing anything")
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    result = execute(project_root, args.dry_run)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
