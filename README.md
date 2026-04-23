# claude-memex

> A documentation management system for Claude Code that turns any project's docs into a **persistent, compounding, LLM-maintained knowledge base** — and enforces that discipline at tool-call time through hooks.

**Status:** alpha — v0.1.0 in development. Not yet published.
**Licence:** [MIT](LICENSE)

---

## Inspired by

This project is directly inspired by Andrej Karpathy's [`llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026), which describes a pattern for **LLM-maintained personal wikis** — raw sources on one side, a compounding wiki of LLM-authored markdown on the other, with the LLM doing all the bookkeeping.

Memex takes that idea and turns it into a Claude Code plugin:

- The wiki pattern becomes a seedable project template (`/memex:init`)
- The discipline that keeps the wiki healthy becomes a layer of Claude Code hooks that **block** tool calls which violate the contract
- The name nods to [Vannevar Bush's Memex](https://en.wikipedia.org/wiki/Memex) — the 1945 vision of a personal, curated, cross-referenced knowledge store that Karpathy's gist also cites

Full attribution in [CREDITS.md](CREDITS.md).

---

## What it is

Memex ships as a **hybrid**:

1. **A Claude Code plugin.** Install it with `/plugin install claude-memex` (or point at the repo directly) and you get a set of slash commands, skills, subagents, and hook scripts.
2. **A seedable template.** Run `/memex:init [profile]` inside any project and Memex scaffolds a `.memex/` tree, a matching `memex.config.json`, and the `CLAUDE.md` / `AGENTS.md` wiring to make the hooks active.

The plugin version-controls the **behaviour** (hook scripts, skills, profiles). Your project owns only its `.memex/` tree and its config. When a hook logic bug is fixed upstream, every project using Memex gets the fix by updating the plugin.

### Profiles

Memex ships with presets you pick at init time:

| Profile | For | Shape |
|---|---|---|
| `engineering-ops` | SaaS / product codebases | `entities/`, `platform/features/`, `platform/systems/`, `workers/`, `workflows/` |
| `research-wiki` | Multi-source research — closest to Karpathy's original gist | `raw/{articles,papers}/`, `wiki/{entities,concepts,summaries,analyses,syntheses}/` |
| `book-companion` | Reading a long book with the LLM | `raw/chapters/`, `wiki/{characters,places,themes,plot-threads}/` |
| `personal-journal` | Self-tracking, reflection | `raw/entries/`, `wiki/{topics,goals,reflections}/` |
| `generic` | Minimal starting point | `topics/`, `index.md`, `log.md`, `.open-questions/` |

All profiles share: `AGENTS.md`, `index.md`, `log.md`, `.open-questions/`. The rest is profile-specific. You can fork any profile, edit `memex.config.json`, and register your own.

---

## How it works

Three things make the wiki stay current instead of rotting:

1. **The schema is a file.** `memex.config.json` declares the allowed folders, the required frontmatter fields, the code-to-doc mappings. Hooks read the config — they don't hard-code rules. This is what makes Memex portable.
2. **Enforcement at tool-call time.** `PreToolUse` hooks block `Write` / `Edit` calls that violate path, README, or frontmatter rules. Stderr tells Claude exactly what was wrong; exit 2 surfaces the message so Claude can self-correct.
3. **Session lifecycle keeps it live.** `SessionStart` injects the index + recent log into Claude's context. `UserPromptSubmit` surfaces the top-3 relevant wiki pages. `Stop` appends a log entry and flags pages whose referenced code was touched without an `updated:` bump.

### Other niceties

- **Unicode-friendly slugs** out of the box — Japanese, Greek, Cyrillic, Arabic, Hebrew, Thai and more. Set `naming.asciiOnly: true` if you want strict ASCII.
- **Opt-in update notifications** — set `hookEvents.sessionStart.updateCheck: true` to get a notice when a newer plugin release is published.
- **Optional `qmd` integration** — set `search.engine: "qmd"` for BM25 + vector retrieval; grep fallback is automatic.
- **Lumioh-to-Memex migration** — `/memex:migrate-from-operations` (tested script) moves a `.operations/` tree to `.memex/` and extracts the matching config.

See [`docs/concepts.md`](docs/concepts.md) for the full model.

---

## Quick start

```bash
# Install the plugin (once)
/plugin install claude-memex

# Scaffold a project
cd my-project
/memex:init engineering-ops

# Ingest a source (research-wiki profile)
/memex:ingest .memex/raw/articles/some-article.md

# Ask the wiki a question
/memex:query "what do we know about authentication flows?"

# Health-check
/memex:lint
```

See [`docs/README.md`](docs/README.md) for the full command reference and cookbook.

---

## Why not just use CLAUDE.md?

`CLAUDE.md` is project memory — one file, read at session start, covering build commands and architectural notes. Memex is complementary, not a replacement:

- CLAUDE.md stays short and stable
- `.memex/` is the multi-page knowledge tree CLAUDE.md *points at*
- Anthropic's [`claude-md-management`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management) plugin rolls session learnings into CLAUDE.md; Memex captures the broader knowledge that doesn't fit in one file

Use both. They solve different problems.

---

## Repo layout (plugin side)

```
claude-memex/
├── .claude-plugin/plugin.json     # Manifest
├── .github/                       # CI workflow, issue / PR templates, CODEOWNERS
├── hooks/
│   ├── hooks.json                 # Event wiring
│   └── scripts/                   # Python hook scripts (+ _lib/ helpers)
├── skills/                        # Auto-invoked skills
├── agents/                        # Subagents
├── commands/                      # Slash commands
├── templates/profiles/            # Seedable profile trees
├── templates/shared/              # Generic starter templates
├── schemas/memex.config.schema.json
├── scripts/migrate_from_operations.py
├── docs/                          # Plugin docs
├── examples/                      # Demo projects (incl. worked research-wiki demo)
├── tests/                         # 227 pytest tests
├── CREDITS.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml                 # pytest / ruff / mypy config
└── README.md
```

See [`docs/concepts.md`](docs/concepts.md) for the concept model and [`docs/README.md`](docs/README.md) for the command reference.

---

## Development

Python 3.10+. Stdlib-only at runtime; pytest / ruff / mypy for development.

```bash
git clone https://github.com/anthril/claude-memex.git
cd claude-memex
python -m pip install -e ".[dev]"

pytest                                    # 227 tests, ~5s
ruff check hooks/ tests/ scripts/         # lint
mypy hooks/                               # type-check
```

CI runs all three across Ubuntu / macOS / Windows on Python 3.10 and 3.12.

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. Profile contributions are especially welcome — the schema is deliberately general enough that new presets should be a pure-data addition.

For bug reports and feature requests, use the issue templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).

For security issues, see [SECURITY.md](SECURITY.md) — please don't file public issues for vulnerabilities.

Community norms are set out in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## Prior art

- Andrej Karpathy, [`llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026) — the conceptual origin.
- Vannevar Bush, ["As We May Think"](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/) (1945) — the Memex essay the name nods to.
- Anthropic's [`claude-md-management`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management) plugin — complementary doc-audit tooling for `CLAUDE.md`.

Full attribution in [CREDITS.md](CREDITS.md).
