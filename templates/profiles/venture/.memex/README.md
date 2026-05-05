---
title: Memex root (venture)
slug: memex-root
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# `.memex/` — venture profile

This profile turns the COMP1100/COMP7110 *Introduction to Software
Innovation* curriculum into a navigable tree. The numeric prefixes (`00-`
through `09-`) encode the customer-development sequence so `phase-router`
can decide "where we are" without parsing every page.

See [AGENTS.md](AGENTS.md) for the binding agent contract. See
[../memex.config.json](../memex.config.json) for the authoritative schema.

## Folder map

### Phase folders

| Folder | Curriculum | Contents |
|---|---|---|
| `00-vision/` | Ch. 1 | `vision-sketch.md`, `day-in-life.md` |
| `01-hypotheses/` | Ch. 2 + 3 | `hypothesis-register.md` (canonical), `bmc-v1.md` (initial guesses) |
| `02-customer-discovery/` | Ch. 3 | `segments/<segment>/{README.md,profile.md,interview-guide.md,early-adopters.md,interviews/interview-NNN.md}`, `test-cards/TC-NNN.md`, `learning-cards/LC-NNN.md` |
| `03-value-proposition/` | Ch. 4 (VPC) | `vpc-<segment>-vN.md` |
| `04-competitors/` | Ch. 4 (competitor) | `competitor-table.md`, `swot/<competitor>/README.md`, `uvp.md`, `insights.md` |
| `05-business-model/` | Ch. 2 | `bmc-vN.md` |
| `06-relationships-channels/` | Ch. 8 | `get-keep-grow.md`, `channel-strategy.md`, `funnel-model.md`, `churn-model.md` |
| `07-validation/` | Ch. 1 | `pivot-refine-log.md` |
| `08-prototype/` | Week 7 | `paper/<slug>.md`, `digital/<slug>/README.md`, `feedback/<slug>.md` |
| `09-mvp/` | Ch. 6 + bridge | `mvp-spec.md`, `mvp-metrics.md`, `tech-stack.md`, `architecture/ADR-NNN-<slug>.md`, `schema/{erd.mmd,migrations-plan.md}`, `deploy/{vercel.md,cloudflare.md}`, `analytics/{events-spec.md,funnel-instrumentation.md}`, `feasibility.md` |

### Infrastructure (every profile has these)

| Folder | Contents |
|---|---|
| `.open-questions/<slug>.md` | Unresolved cross-cutting questions |
| `.project-owner-actions/<slug>.md` | Owner-only blockers (legal, IP, MOUs, payment) |
| `.rules/*.md` | Curriculum guard-rails + venture conventions |
| `.state/` | Plugin-managed per-session state |
| `index.md` | Auto-maintained catalogue |
| `log.md` | Auto-appended chronological ledger |

## How a venture moves

1. **Vision** — `vision-sketch` writes `00-vision/vision-sketch.md` and
   `day-in-life.md`. `hypothesis-register` seeds an initial list of guesses.
2. **Customer discovery** — `customer-segment-define`, `customer-profile-build`,
   `early-adopter-profile`, `interview-guide-build`, `interview-log`,
   `interview-analyse` populate `02-customer-discovery/`. The
   `customer-discovery-status` gate (Ch. 3 four questions) blocks transition
   to MVP work until evidence is sufficient.
3. **Value proposition** — `value-map-build`, `vpc-fit-check` build
   `03-value-proposition/`. Each VPC links to a segment.
4. **Competitor map** — `competitor-discover`, `competitor-table-build`,
   `swot-build`, `competitor-bmc-shadow`, `uvp-statement` populate
   `04-competitors/`.
5. **Business model** — `bmc-build`, `bmc-update` track BMC versions. Each
   hypothesis flip bumps the BMC.
6. **Relationships and channels** — `get-keep-grow-design`, `channel-select`,
   `funnel-model`, `churn-model` populate `06-relationships-channels/`.
7. **Validation** — `pivot-refine-log` records every pivot/refine decision
   with trigger evidence, what changed, what was kept.
8. **Prototype** — `divergent-ideate`, `converge-ideas`, `paper-prototype`,
   `digital-prototype`, `prototype-feedback-collect` produce the prototype
   tree. The `prototype-vs-mvp-distinguish` gate (Ch. 6 5-dimension table)
   refuses to label a prototype as an MVP.
9. **MVP planning** — `mvp-scope`, `mvp-type-select`, `mvp-metrics`,
   `mvp-tech-plan`, `mvp-schema-plan`, `mvp-deploy-plan`, `mvp-analytics-plan`,
   `mvp-feasibility`, `mvp-build-plan`, `pitch-1min-build`. Connector-aware
   skills (Supabase, Cloudflare, Figma, Vercel) probe live infrastructure
   when MCPs are available.

## Three blocking gates

The profile codifies three guard-rails:

1. **Hypothesis falsifiability** — see [`.rules/hypothesis-rules.md`](.rules/hypothesis-rules.md)
2. **Customer-discovery readiness** — see [`.rules/customer-discovery-rules.md`](.rules/customer-discovery-rules.md)
3. **Prototype vs MVP** — see [`.rules/prototype-vs-mvp-rules.md`](.rules/prototype-vs-mvp-rules.md)

Skills can override with `--force`; the override is logged automatically.

## Pivot vs refine

Both pivots and refines are logged in
[`07-validation/pivot-refine-log.md`](07-validation/pivot-refine-log.md). The
rule of thumb: a pivot keeps something from the previous iteration and
changes something else. A refine tweaks the same model. Both must keep what
was learned. See [`.rules/pivot-refine-rules.md`](.rules/pivot-refine-rules.md).
