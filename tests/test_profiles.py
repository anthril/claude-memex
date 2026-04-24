"""Every shipped profile scaffolds cleanly, its config parses, and its canonical path is accepted."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import PROFILES, PROFILES_DIR

CANONICAL_PATHS = {
    "engineering-ops": ".memex/entities/my-entity/README.md",
    "research-wiki": ".memex/wiki/entities/my-entity/README.md",
    "research-project": ".memex/wiki/entities/my-entity/README.md",
    "book-companion": ".memex/wiki/characters/my-character/README.md",
    "personal-journal": ".memex/wiki/topics/my-topic/README.md",
    "generic": ".memex/topics/my-topic/README.md",
}


@pytest.mark.parametrize("profile", PROFILES)
def test_config_parses(profile):
    cfg = json.loads((PROFILES_DIR / profile / "memex.config.json").read_text())
    assert cfg["profile"] == profile
    assert "root" in cfg
    assert "allowedTopLevel" in cfg


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_has_required_files(profile):
    root = PROFILES_DIR / profile
    assert (root / "memex.config.json").exists()
    assert (root / "CLAUDE.md").exists()
    assert (root / ".memex" / "AGENTS.md").exists()
    assert (root / ".memex" / "README.md").exists()
    assert (root / ".memex" / "index.md").exists()
    assert (root / ".memex" / "log.md").exists()
    assert (root / ".memex" / ".open-questions" / "README.md").exists()


@pytest.mark.parametrize("profile", PROFILES)
def test_canonical_path_accepted(profile, project, run_hook):
    proj = project(profile)
    target = proj / CANONICAL_PATHS[profile].replace("/", "\\" if "\\" in str(proj) and False else "/")
    # Use os-independent path construction
    parts = CANONICAL_PATHS[profile].split("/")
    target = Path(proj, *parts)
    rc, _, err = run_hook("path-guard.py", {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
    })
    assert rc == 0, f"{profile}: canonical path blocked — {err}"


@pytest.mark.parametrize("profile", PROFILES)
def test_session_start_works(profile, project, run_hook):
    proj = project(profile)
    rc, out, _ = run_hook("session-start-context.py", {"cwd": str(proj)})
    assert rc == 0
    data = json.loads(out) if out.strip() else {}
    ctx = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "Memex index" in ctx, f"{profile}: no index in SessionStart context"


@pytest.mark.parametrize("profile", PROFILES)
def test_frontmatter_required_on_agents_md(profile, project, run_hook):
    proj = project(profile)
    agents = proj / ".memex" / "AGENTS.md"
    assert agents.exists()
    # AGENTS.md as shipped has valid frontmatter — frontmatter-check should pass
    rc, _, err = run_hook("frontmatter-check.py", {
        "tool_name": "Write",
        "tool_input": {"file_path": str(agents)},
    })
    assert rc == 0, f"{profile}: AGENTS.md failed frontmatter-check — {err}"


@pytest.mark.parametrize("profile", PROFILES)
def test_log_has_parseable_init_entry(profile, project):
    proj = project(profile)
    log = proj / ".memex" / "log.md"
    content = log.read_text()
    # The log must have at least one `## [YYYY-MM-DD] event | subject` entry
    import re
    assert re.search(r"^## \[\d{4}-\d{2}-\d{2}\] \w+ \| ", content, re.MULTILINE), \
        f"{profile}: log.md missing parseable init entry"
