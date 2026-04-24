---
title: Memex root (engineering-ops)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# `.memex/` — engineering-ops profile

This is the Claude-maintained wiki for this project. See [AGENTS.md](AGENTS.md) for the binding contract. See [../memex.config.json](../memex.config.json) for the authoritative schema.

The profile is tailored to a working SaaS or product codebase — planning (PRDs, RFCs, ADRs), building (features, systems, integrations, workers, agents, workflows), and operating (runbooks, processes, environments, incidents, audits).

## Folder map

### Planning — what the team is about to build

| Folder | Contents |
|---|---|
| `planning/roadmap.md` | Rolling roadmap. Editable at will; the single place to check "what's next". |
| `planning/prds/<slug>/README.md` | Product requirement docs — the "why" and "what" before any code. |
| `planning/rfcs/<slug>/README.md` | Request-for-comment design specs — the "how", proposed for review. |
| `planning/decisions/<slug>.md` | Architectural decision records (ADRs). Short, chronological, immutable once accepted. |

### Building — what exists in production

| Folder | Contents |
|---|---|
| `entities/<slug>/README.md` | First-class domain concepts. One folder per entity. |
| `platform/features/<slug>/README.md` | UI surfaces, end-user features, business flows. |
| `platform/systems/<slug>/README.md` | Backend systems, edge functions, service boundaries. |
| `platform/integrations/<slug>/README.md` | Third-party APIs, SDKs, webhooks we consume or expose. |
| `workers/<slug>/README.md` | Scheduled jobs, queue workers, cron tasks. |
| `agents/<slug>/README.md` | AI / LLM-backed agents. |
| `workflows/<slug>/README.md` | Cross-feature flows that span multiple systems. |

### Operating — what keeps it running

| Folder | Contents |
|---|---|
| `runbooks/<slug>/README.md` | Ops / on-call playbooks: trigger, symptom, diagnosis, remediation, escalation. |
| `processes/<slug>/README.md` | Release, CI/CD, onboarding, support, incident response — how the team works. |
| `environments/<slug>/README.md` | prod / staging / dev / local configuration, DNS, secret layout, region plan. |

### Timelined — dated folders, chronological

| Folder | Contents |
|---|---|
| `.audits/DDMMYYYY-HHMM/` | Timestamped audit findings (security, compliance, data integrity, migration). |
| `.research/DDMMYYYY-HHMM/` | Timestamped investigations and spikes. |
| `.incidents/DDMMYYYY-HHMM/` | Blameless postmortems — timeline, impact, root cause, action items. |

### Infrastructure — every profile has these

| Folder | Contents |
|---|---|
| `.open-questions/<slug>.md` | Unresolved cross-cutting questions. Resolved ones move to `.resolved/`. |
| `.rules/*.md` | Project-specific rule documents. |
| `.state/` | Plugin-managed per-session state. Do not hand-edit. |
| `index.md` | Auto-maintained catalogue of wiki pages. |
| `log.md` | Auto-appended chronological ledger. |

## Rules to read first

- [`.rules/documentation-rules.md`](.rules/documentation-rules.md) — path, naming, frontmatter
- [`.rules/planning-rules.md`](.rules/planning-rules.md) — PRD vs RFC vs ADR, decision record lifecycle
- [`.rules/feature-completion-rules.md`](.rules/feature-completion-rules.md) — what "done" means for a feature
- [`.rules/migration-rules.md`](.rules/migration-rules.md) — how schema / database changes get documented
- [`.rules/incident-rules.md`](.rules/incident-rules.md) — blameless postmortem structure
- [`.rules/runbook-rules.md`](.rules/runbook-rules.md) — runbook skeleton

## Enforcement

Every write into this tree is checked by Memex hooks at tool-call time. The hooks read rules from `../memex.config.json`. If a write is blocked, read the stderr message — it tells you exactly what rule was violated and how to fix it.
