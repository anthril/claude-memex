---
title: Memex root (engineering-ops)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# `.memex/` — engineering-ops profile

This is the Claude-maintained wiki for this project. See [AGENTS.md](AGENTS.md) for the binding contract. See [../memex.config.json](../memex.config.json) for the authoritative schema.

## Folder map

| Folder | Contents |
|---|---|
| `entities/<slug>/README.md` | First-class domain concepts. One folder per entity. |
| `platform/features/<slug>/README.md` | UI surfaces, end-user features, business flows. |
| `platform/systems/<slug>/README.md` | Backend systems, edge functions, service boundaries. |
| `workers/<slug>/README.md` | Scheduled jobs, queue workers, cron tasks. |
| `agents/<slug>/README.md` | AI / LLM-backed agents. |
| `workflows/<slug>/README.md` | Cross-feature flows that span multiple systems. |
| `.audits/DDMMYYYY-HHMM/` | Timestamped audit findings (security, data integrity, migration). |
| `.research/DDMMYYYY-HHMM/` | Timestamped investigations and spikes. |
| `.open-questions/<slug>.md` | Unresolved cross-cutting questions. Resolved ones move to `.resolved/`. |
| `.rules/*.md` | Project-specific rule documents. |
| `index.md` | Auto-maintained catalogue of wiki pages. |
| `log.md` | Auto-appended chronological ledger. |

## Rules to read first

- [`.rules/documentation-rules.md`](.rules/documentation-rules.md) — path, naming, frontmatter
- [`.rules/feature-completion-rules.md`](.rules/feature-completion-rules.md) — what "done" means for a feature
- [`.rules/migration-rules.md`](.rules/migration-rules.md) — how database / schema changes get documented

## Enforcement

Every write into this tree is checked by Memex hooks at tool-call time. The hooks read rules from `../memex.config.json`. If a write is blocked, read the stderr message — it tells you exactly what rule was violated and how to fix it.
