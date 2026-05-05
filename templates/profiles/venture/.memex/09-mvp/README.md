---
title: 09 — MVP
slug: phase-mvp
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 09 — MVP

Minimum Viable Product — scope, metrics, and the engineering bridge.

Curriculum source: COMP1100 Ch. 6 + the engineering-bridge skills in
[`@anthril/startup-factory`](https://github.com/anthril/startup-factory).

## Sub-folder structure

```
09-mvp/
├── mvp-spec.md             (KISS feature set)
├── mvp-metrics.md          (success metrics per hypothesis)
├── tech-stack.md           (ADR-style stack decision)
├── architecture/
│   └── ADR-NNN-<slug>.md   (each ADR's folder is readme-required)
├── schema/
│   ├── erd.mmd             (Mermaid ERD)
│   └── migrations-plan.md
├── deploy/
│   ├── vercel.md
│   └── cloudflare.md
├── analytics/
│   ├── events-spec.md
│   └── funnel-instrumentation.md
├── feasibility.md
└── open-questions.md       (rolled up into ../.open-questions/ on Stop)
```

## Required artifacts

| File | Skill |
|---|---|
| `mvp-spec.md` | `mvp-planning/mvp-scope` |
| `mvp-metrics.md` | `mvp-planning/mvp-metrics` |
| `tech-stack.md` | `mvp-planning/mvp-tech-plan` (delegates to `tech-stack-recommender`, `architecture-design`, `adr-writer`) |
| `architecture/ADR-NNN-<slug>.md` | `mvp-planning/adr-writer` (called by every planning skill that lands a decision) |
| `schema/erd.mmd` + `schema/migrations-plan.md` | `mvp-planning/mvp-schema-plan` |
| `deploy/vercel.md` + `deploy/cloudflare.md` | `mvp-planning/mvp-deploy-plan` |
| `analytics/events-spec.md` + `analytics/funnel-instrumentation.md` | `mvp-planning/mvp-analytics-plan` |
| `feasibility.md` | `mvp-planning/mvp-feasibility` |

## The blocking gates

Two gates apply to entering this phase:

1. `customer-discovery-status` (Ch. 3) must return ready
2. `prototype-vs-mvp-distinguish` (Ch. 6) must accept the artifact's
   classification

Both are blocking. Override with `--force`; logged.

## KISS

The MVP is the smallest thing that lets us test the *primary* hypothesis.
Not the second hypothesis. Not nice-to-haves. The `mvp-scope` skill forces
a `cut / keep / maybe` classification.

## Connector-aware skills

Skills in this phase can probe live infrastructure via MCPs:

- **Supabase MCP** — `mvp-planning/supabase-schema-design`,
  `mvp-planning/migration-plan`
- **Cloudflare MCP** — `mvp-planning/cloudflare-deploy-plan`
- **Vercel** (CLI + docs, no MCP) — `mvp-planning/vercel-deploy-plan`

Read-only by default; mutating calls follow the
[connector-confirmation idiom](../../../shared/reference/connector-confirmation.md).
