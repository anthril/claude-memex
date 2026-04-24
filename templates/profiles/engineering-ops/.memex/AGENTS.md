---
title: Agent Contract
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Agent Contract

This document is the binding contract for every agent operating on this project's `.memex/` tree.

## 1. Before starting work

1. Read the README for the surface you're touching (`platform/features/<slug>/README.md`, `entities/<slug>/README.md`, etc.)
2. Check `.open-questions/` for the topic; resolve or link before proceeding
3. Check `.audits/` and `.incidents/` for prior findings on this surface
4. For new work, read `planning/roadmap.md` and any relevant `planning/prds/` or `planning/rfcs/` before writing code
5. Read relevant rules under `.rules/`

## 2. Where documents live

See [README.md](README.md) for the folder map. See [`../memex.config.json`](../memex.config.json) for the authoritative schema (`allowedTopLevel`, `readmeRequired`, `frontmatter.required`).

## 3. Required artifacts

| Trigger | Required doc |
|---|---|
| New product proposal / business ask | `planning/prds/<slug>/README.md` |
| New technical design up for review | `planning/rfcs/<slug>/README.md` |
| Architectural decision | `planning/decisions/<slug>.md` — short, numbered, immutable once accepted |
| New feature (UI surface, business flow) | `platform/features/<slug>/README.md` |
| New backend system (edge function, service) | `platform/systems/<slug>/README.md` |
| New third-party integration (API, SDK, webhook) | `platform/integrations/<slug>/README.md` |
| New long-running job / scheduled task | `workers/<slug>/README.md` |
| New AI agent / LLM-backed flow | `agents/<slug>/README.md` |
| New cross-feature workflow | `workflows/<slug>/README.md` |
| New first-class domain concept | `entities/<slug>/README.md` |
| New on-call / ops playbook | `runbooks/<slug>/README.md` |
| New team process (release, CI/CD, onboarding) | `processes/<slug>/README.md` |
| New or changed environment | `environments/<slug>/README.md` |
| Migration, schema change, security-relevant change | `.audits/DDMMYYYY-HHMM/README.md` with the audit trail |
| Production incident | `.incidents/DDMMYYYY-HHMM/README.md` — blameless postmortem |
| Extended investigation / spike | `.research/DDMMYYYY-HHMM/README.md` with findings |
| Unresolved cross-cutting question | `.open-questions/<slug>.md` |

All `README.md` files require the standard frontmatter block (`title`, `slug`, `type`, `status`, `owner`, `created`, `updated`).

## 4. Planning discipline

- **PRD before RFC, RFC before code.** Don't jump straight to implementation for anything non-trivial. If you skip, file an ADR explaining why.
- **ADRs are immutable.** Once a decision is `accepted`, don't edit it — supersede it with a new ADR that references the prior one.
- **Roadmap is living.** `planning/roadmap.md` has no frontmatter requirement; edit it freely as priorities shift.

## 5. Operating discipline

- **Every incident gets a postmortem.** Within the first session after recovery, file `.incidents/<DDMMYYYY-HHMM>/README.md`. Blameless by contract — see `.rules/incident-rules.md`.
- **Every paging-level system has a runbook.** If an on-call engineer could be woken at 3am by this system, `runbooks/<slug>/README.md` must exist.
- **Every environment is documented.** Prod config drift is the #1 cause of silent failures. `environments/<slug>/README.md` captures region, secrets layout, DNS, dependencies.

## 6. Forbidden actions

- Writing docs outside the taxonomy declared in `memex.config.json`
- Bypassing hooks (never pass `--no-verify`-style flags to work around a block)
- Leaving `TODO` / `TBD` / `XXX` / `FIXME` markers inline — promote them to `.open-questions/` or a `## Open questions` section
- Editing an `accepted` ADR (supersede instead)
- Timestamps with colons or spaces (colons break Windows NTFS)
- Editing `.state/` by hand — it's plugin-managed session state

## 7. Escalation

If a rule seems wrong or too strict, file an entry in `.open-questions/` with the proposed change and rationale. Do not disable the hook.

---

*This contract derives from [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). See the plugin's [CREDITS.md](https://github.com/anthril/claude-memex/blob/main/CREDITS.md) for full attribution.*
