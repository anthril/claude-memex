---
title: Agent Contract
slug: agents-contract
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-23
---

# Agent Contract

This document is the binding contract for every agent operating on this project's `.memex/` tree.

## 1. Before starting work

1. Read the README for the surface you're touching (`platform/features/<slug>/README.md`, `entities/<slug>/README.md`, etc.)
2. Check `.open-questions/` for the topic; resolve or link before proceeding
3. Check `.audits/` for prior findings on this surface
4. Read relevant rules under `.rules/`

## 2. Where documents live

See [README.md](README.md) for the folder map. See [`../memex.config.json`](../memex.config.json) for the authoritative schema (`allowedTopLevel`, `readmeRequired`, `frontmatter.required`).

## 3. Required artifacts

| Trigger | Required doc |
|---|---|
| New feature (UI surface, business flow) | `platform/features/<slug>/README.md` |
| New backend system (edge function, worker, integration) | `platform/systems/<slug>/README.md` |
| New long-running job / scheduled task | `workers/<slug>/README.md` |
| New AI agent / LLM-backed flow | `agents/<slug>/README.md` |
| New cross-feature workflow | `workflows/<slug>/README.md` |
| New first-class domain concept | `entities/<slug>/README.md` |
| Migration, schema change, security-relevant change | `.audits/DDMMYYYY-HHMM/README.md` with the audit trail |
| Extended investigation / spike | `.research/DDMMYYYY-HHMM/README.md` with findings |
| Unresolved cross-cutting question | `.open-questions/<slug>.md` |

All `README.md` files require the standard frontmatter block (`title`, `slug`, `type`, `status`, `owner`, `created`, `updated`).

## 4. Forbidden actions

- Writing docs outside the taxonomy declared in `memex.config.json`
- Bypassing hooks (never pass `--no-verify`-style flags to work around a block)
- Leaving `TODO` / `TBD` / `XXX` markers inline — promote them to `.open-questions/` or a `## Open questions` section
- Timestamps with colons or spaces (colons break Windows NTFS)
- Editing `.state/` by hand — it's plugin-managed session state

## 5. Escalation

If a rule seems wrong or too strict, file an entry in `.open-questions/` with the proposed change and rationale. Do not disable the hook.

---

*This contract derives from [Andrej Karpathy's `llm-wiki.md` gist (2026)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). See the plugin's [CREDITS.md](https://github.com/anthril/claude-memex/blob/main/CREDITS.md) for full attribution.*
