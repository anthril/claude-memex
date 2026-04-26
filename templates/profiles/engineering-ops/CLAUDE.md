# {{ProjectName}} — Claude Instructions

This project uses the [Memex](https://github.com/anthril/claude-memex) plugin to maintain a Claude-authored knowledge base under `.memex/`.

## Agent contract

All agents working in this repo MUST follow [.memex/AGENTS.md](.memex/AGENTS.md) for documentation, folder placement, and feature-completion requirements.

The documentation system is enforced by hooks shipped in the `memex` Claude Code plugin. Edits that bypass it will be blocked at tool-call time.

## Key indices

- [.memex/README.md](.memex/README.md) — folder map
- [.memex/AGENTS.md](.memex/AGENTS.md) — binding contract
- [.memex/index.md](.memex/index.md) — catalogue of wiki pages
- [.memex/log.md](.memex/log.md) — chronological ledger
- [.memex/planning/roadmap.md](.memex/planning/roadmap.md) — rolling roadmap, single source of "what's next"
- [.memex/runbooks/](.memex/runbooks/) — on-call playbooks
- [.memex/.incidents/](.memex/.incidents/) — production postmortems
- [.memex/.open-questions/](.memex/.open-questions/) — unresolved items
- [memex.config.json](memex.config.json) — schema

## How the docsite shows this wiki

The optional [memex-docsite](https://github.com/anthril/claude-memex/blob/main/docs/docsite.md) reads `memex.config.json#/index.sections` for the sidebar's "Sections" nav, and `frontmatter.enum.type` for the page-type badges. This profile maps multiple type enum values into a single section (e.g. Planning ↔ `prd|rfc|decision`); use the schema's array-of-objects form for `index.sections` if you need to override the bridge. Run `memex-docsite serve` (after `pip install -e ".[docsite]"`) to browse this wiki locally.

## Runtime behaviour

- Before any non-trivial task, invoke the `memex-planner` subagent or read the relevant `.memex/` pages directly
- Never leave a question unresolved in prose — file it in `.open-questions/` or the owning doc's `## Open questions`
- When the hook layer blocks a tool call, read the stderr message and fix the cause; do not bypass
- After finishing a task, ensure the touched wiki pages have bumped `updated:` and a changelog entry

## Project-specific additions

<!-- Put project-specific CLAUDE.md content here — build commands, gotchas, etc. -->
