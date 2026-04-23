# Scribe — Repo Plan

> **Working name:** `scribe` (placeholder). Alternatives: `memex` (Vannevar Bush nod from `llm-wiki.md`), `docguard` (pairs with `vibeguard`), `codex-ops`, `operations-kit`. Choose one and search/replace; the design does not depend on the name.

A documentation management system for Claude Code (and compatible agents) that turns project docs into a **persistent, compounding, LLM-maintained knowledge base** — and enforces that discipline at tool-call time through hooks.

It merges two patterns:

| Pattern | Source | What it contributes |
|---|---|---|
| Living wiki maintained by the LLM | `llm-wiki.md` | Compounding synthesis, index + log, ingest/query/lint loop, no human-authored doc |
| Structured, hook-enforced ops tree | Lumioh `.operations/` | Required frontmatter, kebab-case guards, README-per-folder, feature-doc-required, migration-doc-link, blocking at tool-call time |

Neither half alone is enough. RAG-style document piles rot; enforced ops trees don't compound. Scribe is both.

---

## 1. What was reviewed

Verified by direct read:

- `C:\Development\Lumioh\lumioh\.claude\CLAUDE.md`
- `C:\Development\Lumioh\lumioh\.claude\settings.json` (hook wiring)
- `C:\Development\Lumioh\lumioh\.claude\hooks\*.py` — all five hooks: `operations-path-guard.py`, `operations-readme-required.py`, `operations-frontmatter.py`, `feature-doc-required.py`, `migration-doc-link.py`
- `C:\Development\Lumioh\lumioh\.operations\AGENTS.md`, `README.md`
- `C:\Development\Lumioh\lumioh\.operations\.rules\*.md` — `README.md`, `documentation-rules.md`, `feature-completion-rules.md`, `migration-rules.md`, `CONVENTIONS.md`
- `llm-wiki.md` (uploaded)

Verified by web research (Anthropic & Claude Code docs, current as of April 2026):

- Claude Code hook events and I/O contract: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `Notification`, `PermissionRequest`, `Setup`, `TeammateIdle`, `TaskCompleted`, `ConfigChange`, `WorktreeCreate`, `WorktreeRemove`. Matchers for tool events support `tool_name` regex plus per-hook `if` rules with permission-rule syntax (e.g. `"Bash(git *)"`, `"Edit(*.ts)"`). Exit code 2 from stdin-JSON-fed scripts blocks with stderr surfaced to Claude. PreToolUse (v2.0.10+) can mutate `tool_input`. PreToolUse (v2.1.9+) can return `additionalContext`.
- Plugin structure: `.claude-plugin/plugin.json` manifest at plugin root; `commands/`, `agents/`, `skills/`, `hooks/`, `.mcp.json` at plugin root (not nested inside `.claude-plugin/`). Hooks declared in `hooks/hooks.json` (or inline in `plugin.json`). `${CLAUDE_PLUGIN_ROOT}` for portable paths.
- Official `claude-md-management` plugin — confirms Anthropic's own stance that CLAUDE.md should be audited and rolled forward from session learnings. Scribe generalises this to the whole doc tree.

**Not verified:** current contents of `C:\Development\@anthril\` — the Filesystem MCP server stopped responding mid-session after the initial reads, so I could not list the target directory before it went unresponsive. The plan assumes `@anthril` is a namespace folder holding sibling Anthril projects (consistent with the memory context listing `vibe-guard`, `business-context-protocol`, `official-claude-plugins`, `cloudflare-worker-templates`, `research.anthril`). If that assumption is wrong, the repo layout below needs adjusting but nothing else does.

---

## 2. Positioning & distribution form

Scribe ships as a **hybrid**:

1. **Claude Code plugin** (`scribe` inside `C:\Development\anthril\official-claude-plugins\` or a new `@anthril/scribe` repo) — ships the reusable behaviours: skills, slash commands, subagents, hook Python scripts, templates.
2. **Seedable template** — an `/scribe:init` command (shipped by the plugin) that scaffolds `.scribe/`, `.claude/`, `CLAUDE.md`, `AGENTS.md` into any target project. The seed is **parameterised by a profile** (see §7).

This matches how Lumioh already works (project-scoped `.claude/hooks/` calling project-scoped Python scripts with project-scoped `.operations/` rules) but cleanly separates the *library of behaviours* (versioned, installable) from the *project instance* (living under the project's own git history).

Why hybrid and not either alone:

- **Plugin-only** — hooks at user/global scope would apply to every project. That's wrong: doc discipline is project-specific.
- **Template-only** — every project gets its own copy of the hook scripts. No central fix path when a bug is found.
- **Hybrid** — the plugin version-controls the hook logic (`${CLAUDE_PLUGIN_ROOT}/hooks/scripts/*.py`); the project's `.claude/settings.json` points at those scripts; the project owns only its `.scribe/` tree and its `scribe.config.json`.

Trade-off to flag: plugin-shipped hook scripts mean hooks keep working even if the plugin is updated mid-session — in practice this has been fine for Lumioh-like systems but the project owner should pin plugin version in `scribe.config.json`.

---

## 3. Design principles

Carried forward from the two source patterns:

1. **Claude writes the docs, not the human.** The human curates sources, asks questions, reviews diffs. The doc layer is LLM-owned.
2. **Enforcement is at tool-call time, not at review time.** Lumioh's lesson: hooks that `exit 2` with a clear stderr message are ~100× more effective than a doc saying "please follow this convention."
3. **Every doc has a home.** No `docs/`, `notes/`, `WIP/`. Every artifact maps to a slot in the taxonomy. If nothing fits, an open-question file gets filed — never a TODO inline.
4. **Frontmatter is non-negotiable.** `title`, `slug`, `type`, `status`, `owner`, `created`, `updated`. Validated by a PostToolUse hook. Dataview-compatible.
5. **The index and the log.** One content-oriented catalogue (`index.md`), one chronological ledger (`log.md`). Both auto-maintained.
6. **Open questions are a first-class artifact.** Unresolved prose TODOs are banned; they get promoted to `.open-questions/` (cross-cutting) or to a scoped `## Open questions` section on the owning doc.
7. **Compounding, not rediscovery.** When a new source is ingested or a task completes, the wiki gets updated — entity pages extended, contradictions flagged, changelogs bumped. The wiki is never re-derived from scratch.
8. **Adversarial mindset.** The hook layer treats Claude (and humans) as adversaries that will try to write ad-hoc docs in `src/notes/`. Block it. Make the right path the easy one.

New, not in either source:

9. **The schema is a file, not a convention.** `scribe.config.json` declares the folders, the required READMEs, the frontmatter fields. Hooks read the config instead of hard-coding rules. This is what makes Scribe portable beyond Lumioh's SaaS-platform-specific taxonomy.
10. **Profiles.** Engineering-ops, research-wiki, book-companion, personal-journal — each a preset schema. Users pick one at init or write their own.

---

## 4. Repo layout (the plugin side)

Proposed tree for `C:\Development\@anthril\scribe\` (plugin repo):

```
scribe/
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest
├── hooks/
│   ├── hooks.json                  # Event wiring
│   └── scripts/
│       ├── _lib/
│       │   ├── config.py           # Reads scribe.config.json
│       │   ├── frontmatter.py      # Parse/validate YAML frontmatter
│       │   ├── paths.py            # Find scribe root, resolve targets
│       │   └── state.py            # Per-session state under .scribe/.state/
│       ├── path-guard.py           # Kebab-case, dated folder, top-level allowlist
│       ├── readme-required.py      # README-per-folder gate
│       ├── frontmatter-check.py    # Required fields validator
│       ├── doc-required.py         # Generalisation of Lumioh feature-doc-required
│       ├── ingest-doc-link.py      # Generalisation of migration-doc-link
│       ├── session-start-context.py  # Injects index.md head + recent log
│       ├── user-prompt-context.py  # Surfaces relevant pages for the prompt
│       ├── stop-log-append.py     # Appends log entry when session stops
│       ├── stop-stale-check.py    # Flags docs touched-but-not-updated
│       └── precompact-snapshot.py  # Writes synthesis before compaction
├── skills/
│   ├── ingest-source/
│   │   └── SKILL.md                # Reads a raw source, updates wiki pages
│   ├── doc-query/
│   │   └── SKILL.md                # Synthesises answer from wiki pages
│   ├── wiki-lint/
│   │   └── SKILL.md                # Health-check: contradictions, orphans, stale claims
│   ├── open-questions-triage/
│   │   └── SKILL.md                # Sort, resolve, archive
│   └── doc-refactor/
│       └── SKILL.md                # Split/merge pages, fix cross-references
├── agents/
│   ├── scribe-ingestor.md          # Subagent for single-source ingest (isolated)
│   ├── scribe-linter.md            # Subagent for wiki-lint passes
│   └── scribe-planner.md           # Reads wiki to plan work before a task
├── commands/
│   ├── scribe-init.md              # /scribe:init — scaffold a project
│   ├── scribe-ingest.md            # /scribe:ingest <source>
│   ├── scribe-query.md             # /scribe:query <question>
│   ├── scribe-lint.md              # /scribe:lint
│   ├── scribe-log.md               # /scribe:log — view/edit log.md
│   └── scribe-open-q.md            # /scribe:open-q — file an open question
├── templates/                      # Scaffolded by /scribe:init
│   ├── profiles/
│   │   ├── engineering-ops/        # Lumioh-shaped: features/systems/entities/...
│   │   │   ├── scribe.config.json
│   │   │   ├── .scribe/            # Initial tree: AGENTS.md, README.md, .rules/, .open-questions/, etc.
│   │   │   ├── CLAUDE.md
│   │   │   └── settings.json       # Claude settings patch to append
│   │   ├── research-wiki/          # llm-wiki-shaped: raw/, wiki/, index.md, log.md
│   │   ├── book-companion/
│   │   ├── personal-journal/
│   │   └── generic/                # Minimal: just index, log, one topical folder
│   └── shared/
│       ├── frontmatter.md.tmpl
│       ├── agents.md.tmpl
│       └── claude.md.tmpl
├── docs/
│   ├── README.md                   # Scribe's own docs (eat own food)
│   ├── concepts.md                 # Plugin concepts: profiles, hooks, schema
│   ├── hook-catalog.md             # Every hook, what it does, when it fires
│   ├── profile-authoring.md        # How to write a profile
│   └── cookbook.md                 # Recipes: adding a custom folder, etc.
├── examples/
│   ├── engineering-ops-demo/       # Fully scaffolded example project
│   └── research-wiki-demo/
├── README.md
├── LICENSE
└── package.json                    # Version tracking; optional npm distribution
```

Design notes:

- **Hooks live in the plugin**, not in the target project. The target project's `.claude/settings.json` references `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...`. This is the single biggest improvement over the Lumioh pattern: central fix path when a hook logic bug is found.
- **`_lib/`** centralises shared hook utilities (reading `scribe.config.json`, finding the project root, parsing frontmatter). In Lumioh these utilities are copy-pasted across five files; Scribe deduplicates them.
- **Profiles** are full template trees, not just JSON. `/scribe:init engineering-ops` copies the whole subtree.
- **Skills vs commands vs agents:** skills auto-load when Claude sees a matching context (e.g. "ingest this article" triggers `ingest-source`); commands are user-invoked (`/scribe:ingest path/to.md`); agents run in isolated turns for specific bounded tasks (single-source ingest is a natural subagent — isolated context, deterministic output).

---

## 5. Repo layout (the project side — seeded by `/scribe:init`)

What a target project looks like after init with the `engineering-ops` profile (close to Lumioh):

```
my-project/
├── .claude/
│   ├── CLAUDE.md                   # Points at AGENTS.md, summarises contract
│   └── settings.json               # Appends Scribe hook wiring to whatever exists
├── .scribe/
│   ├── scribe.config.json          # Schema + profile version + overrides
│   ├── AGENTS.md                   # Binding contract
│   ├── README.md                   # Folder map + schema reference
│   ├── index.md                    # Auto-maintained catalogue
│   ├── log.md                      # Auto-maintained chronological ledger
│   ├── .state/                     # Per-session state (gitignored)
│   ├── .rules/
│   │   ├── README.md
│   │   ├── documentation-rules.md
│   │   ├── feature-completion-rules.md
│   │   └── ...
│   ├── .audits/                    # DDMMYYYY-HHMM folders
│   ├── .research/                  # DDMMYYYY-HHMM folders
│   ├── .open-questions/
│   │   └── .resolved/
│   ├── entities/
│   ├── platform/
│   │   ├── features/
│   │   └── systems/
│   ├── workers/
│   ├── workflows/
│   └── agents/
└── [the project's actual code]
```

With the `research-wiki` profile:

```
my-project/
├── .claude/
│   ├── CLAUDE.md
│   └── settings.json
├── .scribe/
│   ├── scribe.config.json
│   ├── AGENTS.md
│   ├── README.md
│   ├── index.md
│   ├── log.md
│   ├── .state/
│   ├── raw/                        # Immutable sources (articles, papers, images)
│   │   ├── articles/
│   │   ├── papers/
│   │   └── assets/
│   ├── wiki/
│   │   ├── entities/               # Named things: people, orgs, products
│   │   ├── concepts/               # Abstract ideas
│   │   ├── summaries/              # One per raw source
│   │   ├── analyses/               # User-driven explorations, filed back
│   │   └── syntheses/              # Cross-source synthesis pages
│   └── .open-questions/
```

Both profiles share: `scribe.config.json`, `AGENTS.md`, `README.md`, `index.md`, `log.md`, `.open-questions/`, `.state/`. Everything else is profile-specific.

**Naming convention:** I'm using `.scribe/` rather than `.operations/` for three reasons: (1) `operations` is domain-specific to Lumioh; (2) the dot-prefix matches `.claude/`, `.vguard/` and keeps the top level clean; (3) `scribe` is the working plugin name so the correspondence is clear. Rename in the config if preferred; the hooks read the folder name from `scribe.config.json`.

---

## 6. `scribe.config.json` — the schema file

This is what makes Scribe reusable. Hooks read this instead of hard-coding rules.

```json
{
  "$schema": "https://raw.githubusercontent.com/<org>/scribe/main/schemas/scribe.config.schema.json",
  "version": "1",
  "profile": "engineering-ops",
  "pluginVersion": "0.3.0",

  "root": ".scribe",

  "allowedTopLevel": [
    "README.md", "AGENTS.md",
    ".audits", ".research", ".open-questions", ".rules", ".state",
    "entities", "platform", "workers", "workflows", "agents",
    "index.md", "log.md"
  ],

  "datedFolders": {
    "paths": [".audits", ".research"],
    "format": "DDMMYYYY-HHMM"
  },

  "readmeRequired": [
    "platform/features/*",
    "platform/systems/*",
    "entities/*",
    "workers/*",
    "agents/*"
  ],

  "frontmatter": {
    "appliesTo": ["**/README.md", "**/AGENTS.md"],
    "required": ["title", "slug", "type", "status", "owner", "created", "updated"],
    "enum": {
      "type": ["feature", "system", "entity", "worker", "agent", "open-question", "rule"],
      "status": ["draft", "active", "deprecated"]
    }
  },

  "naming": {
    "filePattern": "^(\\d{2}-)?[a-z0-9]+(-[a-z0-9]+)*\\.[a-z0-9]+$",
    "folderPattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
    "exceptions": ["README.md", "AGENTS.md", "CHANGELOG.md", "CONVENTIONS.md", ".resolved"]
  },

  "codeToDocMapping": [
    {
      "codePattern": "src/app/(console)/console/(dashboard)/*/",
      "requiresDoc": "platform/features/{1}/README.md",
      "severity": "warn-then-block",
      "stateKey": "feature"
    },
    {
      "codePattern": "supabase/functions/*/",
      "requiresDoc": "platform/systems/{1}/README.md OR platform/features/*/README.md (referencing)",
      "severity": "warn-then-block"
    },
    {
      "codePattern": "supabase/migrations/*.sql",
      "requiresDoc": "ANY .md containing the slug OR header comment `-- Doc: .scribe/<path>.md`",
      "severity": "block"
    }
  ],

  "hookEvents": {
    "sessionStart": { "injectIndex": true, "injectRecentLog": 5 },
    "userPromptSubmit": { "searchWiki": true, "maxContextPages": 3 },
    "stop": { "appendLog": true, "staleCheck": true },
    "preCompact": { "snapshot": true }
  },

  "log": {
    "path": "log.md",
    "entryPrefix": "## [{YYYY-MM-DD}] {event} | {subject}"
  },

  "index": {
    "path": "index.md",
    "sections": ["Entities", "Concepts", "Features", "Systems", "Open Questions", "Recent Activity"]
  }
}
```

Hook scripts all start the same way:

```python
# hooks/scripts/_lib/config.py
def load_config(project_root: str) -> dict:
    path = os.path.join(project_root, ".scribe", "scribe.config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

This is the single most important abstraction in Scribe — it's what lets the same hook script enforce Lumioh-shaped rules in one project and research-wiki rules in another.

---

## 7. Hook catalog

The full hook surface area Scribe ships. Each entry: name, event, matcher, purpose, behaviour on violation.

### PreToolUse (blocking gates)

| Hook | Matcher | Purpose | On violation |
|---|---|---|---|
| `path-guard.py` | `Write\|Edit` | Kebab-case, dated-folder format, top-level allowlist for `.scribe/`. Generalisation of Lumioh's `operations-path-guard`. Reads allowed list from `scribe.config.json`. | `exit 2`, stderr explains the exact rule violated |
| `readme-required.py` | `Write` | Before writing any non-README file into a README-required folder, require `README.md` to exist in that folder (or the current write must itself be the README). Generalisation of Lumioh's `operations-readme-required`. | `exit 2`, suggests creating the README with the required frontmatter |
| `doc-required.py` | `Write\|Edit` | For each `codeToDocMapping` entry: if code is being written in a tracked pattern and no doc exists, warn on first offence, block on second (session-scoped state in `.scribe/.state/`). Generalisation of `feature-doc-required`. | Warn then block |
| `ingest-doc-link.py` | `Write` | For migration-like artifacts (any pattern declared in `codeToDocMapping` with `severity: block`): require a header comment referencing a `.scribe/` doc, or require that the slug is referenced somewhere in `.scribe/*.md`. Generalisation of `migration-doc-link`. | `exit 2`, suggests both the header-comment form and the cross-link form |
| `frontmatter-precheck.py` | `Edit` on `.scribe/**/README.md` | When *editing* an existing README, confirm the frontmatter still parses before the edit lands. Optional; belt-and-braces with the PostToolUse check. | Warn |

### PostToolUse (validators)

| Hook | Matcher | Purpose | On violation |
|---|---|---|---|
| `frontmatter-check.py` | `Write\|Edit` | After any `.scribe/**/README.md` or `.scribe/**/AGENTS.md` edit, validate required fields. Verifies `updated:` was bumped (compares previous commit hash or last-read state). | `exit 2`, lists missing fields |
| `index-update.py` | `Write\|Edit` | After writing a new page under `.scribe/`, surface a suggestion for the `index.md` entry. Non-blocking — just `additionalContext` to nudge Claude to update the index in the same turn. | `additionalContext` only |

### SessionStart

| Hook | Purpose |
|---|---|
| `session-start-context.py` | Reads `index.md` head + last N `log.md` entries. Emits them as `additionalContext` so Claude sees them at session boot without the user typing anything. N is configurable in `scribe.config.json`. |

### UserPromptSubmit

| Hook | Purpose |
|---|---|
| `user-prompt-context.py` | Extracts keywords from the prompt, greps `.scribe/` for matching page titles and frontmatter, surfaces top-3 page paths + 1-line summaries as `additionalContext`. This is the poor-man's RAG; it's the llm-wiki pattern of "index lookup instead of embeddings." Optional `qmd` integration if installed (BM25 + vector). |

### Stop

| Hook | Purpose |
|---|---|
| `stop-log-append.py` | Appends a `log.md` entry for the session (what was ingested, queried, or changed). Uses conversation transcript + tool-call log to summarise. |
| `stop-stale-check.py` | For every `.scribe/` page whose *referenced* code was touched in the session but whose `updated:` frontmatter was NOT bumped → list them, emit `additionalContext` to the next turn or surface in stderr. This is how the wiki stays in sync with code. |
| `stop-open-questions-check.py` | Greps the session's tool-call transcript for the phrase "TODO" or "TBD" appearing in any `.scribe/` doc Claude wrote; if found, proposes promoting to `.open-questions/`. |

### PreCompact

| Hook | Purpose |
|---|---|
| `precompact-snapshot.py` | Before the conversation compacts, writes a session-summary file to `.scribe/.state/sessions/<session-id>.md` (gitignored by default, opt-in to commit). Preserves the synthesis that would otherwise be lost. |

### SessionEnd

| Hook | Purpose |
|---|---|
| `session-end-log.py` | Final entry in `log.md` with session duration, tool-call counts, pages touched. Useful for the "Agents Behaving Badly" research. |

### Hook wiring (`hooks/hooks.json`)

Plugin-declared, resolved against `${CLAUDE_PLUGIN_ROOT}`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-start-context.py", "timeout": 5000 }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/user-prompt-context.py", "timeout": 5000 }] }
    ],
    "PreToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/path-guard.py", "timeout": 5000 },
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/doc-required.py", "timeout": 5000 }
        ]
      },
      { "matcher": "Write",
        "hooks": [
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/readme-required.py", "timeout": 5000 },
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/ingest-doc-link.py", "timeout": 5000 }
        ]
      }
    ],
    "PostToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/frontmatter-check.py", "timeout": 5000 },
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/index-update.py", "timeout": 5000 }
        ]
      }
    ],
    "Stop": [
      { "hooks": [
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-log-append.py", "timeout": 10000 },
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-stale-check.py", "timeout": 10000 },
          { "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-open-questions-check.py", "timeout": 5000 }
        ]
      }
    ],
    "PreCompact": [
      { "hooks": [{ "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/precompact-snapshot.py", "timeout": 10000 }] }
    ],
    "SessionEnd": [
      { "hooks": [{ "type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-end-log.py", "timeout": 5000 }] }
    ]
  }
}
```

The project's own `.claude/settings.json` does **not** need to duplicate this — plugin hooks are loaded automatically when the plugin is enabled.

---

## 8. Skills, commands, subagents

### Skills (auto-invoked)

| Skill | Trigger phrases | What it does |
|---|---|---|
| `ingest-source` | "ingest this", "process this article/paper", "add this to the wiki", any user message containing a path to a new file under `.scribe/raw/` | Reads the source, summarises to `.scribe/wiki/summaries/<slug>.md` (or equivalent per profile), extracts entities/concepts, updates or creates their pages, updates `index.md`, appends `log.md` |
| `doc-query` | "what does the wiki say about", "based on my docs", "find in my notes" | Searches index → reads relevant pages → synthesises cited answer. Offers to file the answer back as `.scribe/wiki/analyses/<slug>.md` |
| `wiki-lint` | "lint the wiki", "audit my docs", "health check the wiki" | Orphans, contradictions, stale claims, pages referenced but missing, open-questions overdue. Produces a report; offers to auto-fix the easy ones |
| `open-questions-triage` | "triage open questions", "what's blocking me" | Reads `.open-questions/`, groups by topic/age, proposes resolutions or promotions |
| `doc-refactor` | "split this page", "merge these", "rename this slug across the wiki" | Structural edits with automatic cross-reference updates |

### Commands (user-invoked)

| Command | Signature | Notes |
|---|---|---|
| `/scribe:init` | `/scribe:init [profile]` | Scaffolds `.scribe/`, `.claude/`, `CLAUDE.md`, `AGENTS.md`. Refuses to overwrite; if `.scribe/` exists it prints what's missing from the target profile |
| `/scribe:ingest` | `/scribe:ingest <path>` | Explicit invocation of `ingest-source` |
| `/scribe:query` | `/scribe:query <question>` | Explicit invocation of `doc-query` |
| `/scribe:lint` | `/scribe:lint [scope]` | `wiki-lint`; scope can be a folder |
| `/scribe:log` | `/scribe:log [--tail N]` | Prints recent log; `--edit` opens for manual entry |
| `/scribe:open-q` | `/scribe:open-q <title>` | Files a new open question with template |
| `/scribe:promote` | `/scribe:promote <doc-path> <target-type>` | Promotes a `.research/` snippet to a permanent entity/concept page |
| `/scribe:graph` | `/scribe:graph [--format mermaid\|dot]` | Emits a link graph — feeds the "is this orphaned?" view |

### Subagents (isolated execution)

| Agent | When used |
|---|---|
| `scribe-ingestor` | When ingesting large/multi-part sources. Runs in worktree isolation so a long ingest doesn't bloat the main session's context |
| `scribe-linter` | `wiki-lint` on large wikis — runs as a subagent, returns summary |
| `scribe-planner` | Before a non-trivial coding task: reads relevant wiki pages + open questions, produces a plan. Invoked at the top of `feature-completion`-style flows |

Agents use the `isolation: "worktree"` option where isolation matters (ingest, lint) so they don't pollute the main chat's context.

---

## 9. `CLAUDE.md` and `AGENTS.md` templates

### `CLAUDE.md` (project root) — seeded template

```markdown
# {{ProjectName}} — Claude Instructions

## Agent contract

All agents working in this repo MUST follow [.scribe/AGENTS.md](../.scribe/AGENTS.md) for documentation, folder placement, and feature-completion requirements.

The documentation system is enforced by hooks shipped in the `scribe` Claude Code plugin. Edits that bypass it will be blocked at tool-call time.

## Key indices

- [.scribe/README.md](../.scribe/README.md) — folder map + schema
- [.scribe/AGENTS.md](../.scribe/AGENTS.md) — binding contract
- [.scribe/index.md](../.scribe/index.md) — catalogue of wiki pages
- [.scribe/log.md](../.scribe/log.md) — chronological ledger
- [.scribe/.open-questions/](../.scribe/.open-questions/) — unresolved items
- [.scribe/scribe.config.json](../.scribe/scribe.config.json) — schema

## Runtime behaviour

- Before any non-trivial task, invoke the `scribe-planner` subagent or read relevant pages from `.scribe/` directly
- Never leave a question unresolved in prose — file it in `.open-questions/` or the owning doc's `## Open questions`
- When the hook layer blocks a tool call, read the stderr message and fix the cause; do not bypass
- After finishing a task, ensure the touched wiki pages have bumped `updated:` and a changelog entry

## Project-specific additions

<!-- Put project-specific CLAUDE.md content here — build commands, gotchas, etc. -->
```

### `.scribe/AGENTS.md` — binding contract (generic skeleton)

```markdown
---
title: Agent Contract
slug: agents-contract
type: rule
status: active
owner: {{owner}}
created: {{date}}
updated: {{date}}
---

# Agent Contract

This document is the binding contract for every agent operating on this project.

## 1. Before starting work

1. Read the relevant README for the surface you're touching.
2. Check `.open-questions/` for the topic; resolve or link before proceeding.
3. Check `.audits/` for prior findings.
4. Read relevant rules in `.rules/`.

## 2. Where documents live

See [README.md](README.md) for the folder map and [scribe.config.json](scribe.config.json) for the authoritative schema.

## 3. Required artifacts

<!-- Profile-specific content injected at init time -->

## 4. Forbidden actions

- Writing docs outside the taxonomy
- Bypassing hooks
- Leaving TBDs/TODOs inline
- Using timestamps with colons or spaces
- Editing `.scribe/.state/` by hand

## 5. Escalation

If a rule seems wrong, open an entry in `.open-questions/` — do not disable the hook.
```

Both templates are profile-aware — the `engineering-ops` profile injects the Lumioh-style section-4 table; the `research-wiki` profile injects an ingest/query/lint workflow table; etc.

---

## 10. Profiles — what ships out of the box

| Profile | Use case | Top-level folders | Key hooks |
|---|---|---|---|
| `engineering-ops` | SaaS/product codebases (Lumioh-shaped) | `entities/`, `platform/features/`, `platform/systems/`, `workers/`, `workflows/`, `.audits/`, `.research/`, `.open-questions/`, `.rules/` | All, including `codeToDocMapping` for features/systems/migrations |
| `research-wiki` | Multi-source research project | `raw/`, `wiki/entities/`, `wiki/concepts/`, `wiki/summaries/`, `wiki/analyses/`, `wiki/syntheses/`, `.open-questions/` | `ingest`-style, `session-start-context`, `user-prompt-context`, `wiki-lint` |
| `book-companion` | Reading a long book with the LLM | `raw/chapters/`, `wiki/characters/`, `wiki/places/`, `wiki/themes/`, `wiki/plot-threads/`, `timeline.md` | Ingest-per-chapter, entity cross-referencing, no code-mapping |
| `personal-journal` | Self-tracking / reflection | `raw/entries/`, `wiki/topics/`, `wiki/goals/`, `reflections/`, `.open-questions/` | Minimal enforcement; focus on `stop-log-append` and `wiki-lint` |
| `generic` | Start-from-minimal | `index.md`, `log.md`, one `topics/` folder, `.open-questions/` | Only path-guard + frontmatter |

Each profile is a full tree under `templates/profiles/<name>/` that `/scribe:init` copies. Users can fork a profile, edit `scribe.config.json`, and register their own.

---

## 11. Integration with existing `.claude/` and project assets

Scribe does not replace `CLAUDE.md`. Anthropic's own guidance (and the `claude-md-management` plugin) treats CLAUDE.md as project memory. Scribe adds:

- A `.scribe/` tree that CLAUDE.md *points at* — CLAUDE.md stays short and stable
- Hooks that keep `.scribe/` current in a way the CLAUDE.md management plugin does not attempt
- A complementary workflow: `/revise-claude-md` (from the official plugin) captures CLAUDE.md-level learnings; `/scribe:ingest` and the Stop hooks capture wiki-level knowledge

For projects already using VGuard (your case): Scribe's hooks layer on top. Lumioh's `.claude/settings.json` shows the composition already works — VGuard and `.operations/` hooks co-exist. Scribe's hooks run after VGuard's on the same events.

For projects already using Lumioh's `.operations/`: a migration helper (`/scribe:migrate-from-operations`) rewrites `.operations/` → `.scribe/` and generates the matching `scribe.config.json`. Zero content loss — just a rename and a schema extraction.

---

## 12. Adaptation of the `llm-wiki.md` patterns

How each llm-wiki idea lands in Scribe:

| `llm-wiki.md` concept | Scribe implementation |
|---|---|
| Three layers: raw / wiki / schema | `research-wiki` profile's `raw/` + `wiki/` + `scribe.config.json`. Engineering profile compresses raw into the real code |
| Ingest / query / lint | `/scribe:ingest`, `/scribe:query`, `/scribe:lint` + the matching skills |
| `index.md` (content-oriented) | Generated + maintained, auto-updated by `index-update.py` PostToolUse hook |
| `log.md` (chronological, parseable prefix) | Auto-appended by `stop-log-append.py` using the exact `## [YYYY-MM-DD] event \| subject` prefix from llm-wiki. `grep "^## \[" log.md \| tail -5` works out of the box |
| Obsidian-as-IDE | `.scribe/` is a plain markdown tree; Obsidian works on it unchanged. Frontmatter is Dataview-compatible |
| qmd (on-device search) | Optional integration — `user-prompt-context.py` calls `qmd` if installed, falls back to plain grep otherwise |
| "Cross-references are already there" | Enforced by `wiki-lint` (orphan detection) and by the ingest skill (which updates every referenced page, not just the new summary) |
| Memex homage | Acknowledged in docs; `memex` is the alt name |

What llm-wiki leaves abstract and Scribe makes concrete:

- **Who owns what file** → frontmatter `owner` field, enforced
- **When does a new folder get created** → not without a config update + open-question, enforced by path-guard
- **What happens when the wiki drifts from the code** → `stop-stale-check.py` catches it

---

## 13. Build phases

A practical sequencing. Each phase is shippable on its own — you could stop at Phase 2 and still have a useful tool.

### Phase 0 — Decisions and repo scaffold (1 session)
- Confirm name and location
- Create `C:\Development\@anthril\scribe\` with `README.md`, `LICENSE`, `.claude-plugin/plugin.json` stub
- Write `docs/concepts.md` fixing terminology
- **Exit criteria:** empty plugin that loads without error

### Phase 1 — Core enforcement (1-2 sessions)
- `_lib/config.py`, `_lib/frontmatter.py`, `_lib/paths.py`
- Port and generalise Lumioh's 5 hooks → Scribe's `path-guard`, `readme-required`, `frontmatter-check`, `doc-required`, `ingest-doc-link`
- Write `scribe.config.schema.json`
- `templates/profiles/engineering-ops/` — full tree matching Lumioh's `.operations/` structure
- `commands/scribe-init.md`
- **Exit criteria:** `/scribe:init engineering-ops` on a new project produces a working doc tree; writing violating paths gets blocked; Lumioh could switch to Scribe without content changes

### Phase 2 — Session-lifecycle hooks (1 session)
- `session-start-context.py`, `user-prompt-context.py`
- `stop-log-append.py`, `stop-stale-check.py`
- `precompact-snapshot.py`, `session-end-log.py`
- `templates/profiles/generic/`
- **Exit criteria:** on a fresh project, starting a session shows the index and recent log; stopping a session appends a log entry; touched-but-not-bumped pages surface at stop

### Phase 3 — Wiki operations (2 sessions)
- `skills/ingest-source/SKILL.md`, `skills/doc-query/SKILL.md`, `skills/wiki-lint/SKILL.md`
- `commands/scribe-ingest.md`, `scribe-query.md`, `scribe-lint.md`, `scribe-log.md`, `scribe-open-q.md`
- `templates/profiles/research-wiki/`
- `agents/scribe-ingestor.md`, `scribe-linter.md`
- **Exit criteria:** ingest an article end-to-end: it appears in summaries, entities get created/updated, log appended, index updated

### Phase 4 — Advanced (as needed)
- `scribe-planner` subagent
- `doc-refactor` skill
- `/scribe:graph`
- `templates/profiles/book-companion/`, `personal-journal/`
- `/scribe:migrate-from-operations` helper
- Optional qmd integration in `user-prompt-context.py`

### Phase 5 — Publish
- Test on one real Anthril project (Lumioh, Vibeguard, research.anthril — pick one to dogfood)
- Add to `C:\Development\anthril\official-claude-plugins\` marketplace if promoting
- Substack posts: concept piece + hook catalog (drafts in the gists folder)

---

## 14. What this unlocks for your existing work

This is the "so what" — why Scribe is worth building for you specifically, given what's already in memory:

- **VGuard research ("Agents Behaving Badly" on Substack):** Scribe's `log.md` + `.state/sessions/` give you a structured per-session record that's easy to analyse. The research question becomes much more tractable — you have ground truth on what Claude touched, what docs drifted, what was caught vs missed.
- **Lumioh:** the existing `.operations/` system becomes a first-party profile. Fewer bespoke scripts, a clearer upgrade path, and the same discipline generalised to other Anthril projects.
- **Web Lifter cloud console:** right now you flagged "no documentation page" as a gap. Scribe's `research-wiki` profile for the client-facing side + `engineering-ops` for the platform side = two instances of the same tool.
- **Anthril itself:** the company's own research library (papers, internal memos, product decisions) fits the `research-wiki` profile cleanly. `research.anthril` could adopt it.
- **Skill library at `C:\Development\ai-cookbook\skills`:** Scribe's skill definitions follow the same pattern you already use — `argument-hint`, `allowed-tools`, `context`, `agent` fields — with frontmatter enforcement baked in.

---

## 15. Open questions (for your decision)

These materially change the plan if answered differently. I have not guessed — they are listed so you can decide:

1. **Name.** `scribe` / `memex` / `docguard` / something else? (Affects all identifiers but nothing structural.)
2. **Repo location.** `C:\Development\@anthril\scribe\` vs placed inside `C:\Development\anthril\official-claude-plugins\scribe\`? The former is consistent with existing `@anthril\vibe-guard\` and `@anthril\business-context-protocol\`.
3. **Python vs Node/TypeScript for hook scripts.** Lumioh uses Python for `.operations/` hooks and Node for VGuard hooks. Python is cleaner for text processing; Node gives you shared code with VGuard. Recommend Python for portability (no `npm install` in a fresh clone) but flag.
4. **First profile to polish.** `engineering-ops` (fastest win, Lumioh port) or `research-wiki` (more differentiated, aligned with llm-wiki.md)?
5. **Publish publicly or keep @anthril internal first?** Affects the README tone and whether the gists (§concept piece, §hook catalog) are published now or after v1 hardening.
6. **Interaction with `claude-md-management` plugin.** Recommend / require / ignore? My draft recommends complementary use but the boundary could be sharper.
7. **Do we want embeddings / qmd / real RAG in `user-prompt-context.py`, or start with grep-only?** llm-wiki.md makes the case that grep-on-index works to ~100 sources. I recommend grep-only for v1.

None of these block Phase 0 or Phase 1. They can all be answered during Phase 2 or 3.

---

## 16. Supporting gists for publication

Two companion markdown files sit alongside this plan, ready to become Substack posts or GitHub gists:

- `gist-concept-piece.md` — "Beyond CLAUDE.md: Claude-Maintained Project Memory" — the concept / why-this-matters piece. Fits the "Agents Behaving Badly" Substack series as a methodology post.
- `gist-hook-catalog.md` — "A Hook Catalog for Enforcing Doc Discipline in Claude Code" — the technical reference, reusable by anyone building similar enforcement.

Both are written to stand alone — no Scribe-specific assumptions — so they work as publication pieces regardless of what happens with the Scribe repo.

---

## 17. Appendix — key references

- Claude Code hooks reference: `https://code.claude.com/docs/en/hooks`
- Claude Code plugins reference: `https://code.claude.com/docs/en/plugins-reference`
- Agent SDK hooks guide: `https://platform.claude.com/docs/en/agent-sdk/hooks`
- `claude-md-management` plugin: `https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management`
- Lumioh `.operations/` (your reference implementation): `C:\Development\Lumioh\lumioh\.operations\`
- `llm-wiki.md` (uploaded, concept source)
- Vannevar Bush, "As We May Think" (1945) — the Memex essay
