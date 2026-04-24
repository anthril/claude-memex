---
title: Planning
slug: planning-root
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Planning

The "before code" tree. Three artefact types — each distinct, don't mix them.

| Subfolder | Artefact | When |
|---|---|---|
| `prds/<slug>/README.md` | Product requirement doc | Before any non-trivial feature. What and why; not how. |
| `rfcs/<slug>/README.md` | Technical design, up for review | Whenever the implementation approach isn't obvious or multiple engineers will touch the surface. |
| `decisions/<slug>.md` | Architectural decision record (ADR) | Whenever a decision is made that future engineers will wonder about. Short, numbered, immutable once accepted. |
| `roadmap.md` | Rolling roadmap | Lives here; edit freely. |

See [`.rules/planning-rules.md`](../.rules/planning-rules.md) for the required shape of each artefact.
