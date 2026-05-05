---
title: 01 — Hypotheses
slug: phase-hypotheses
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 01 — Hypotheses

Canonical list of every hypothesis the venture is testing, plus the
initial Business Model Canvas (a flat sheet of guesses until customer
discovery finds evidence).

Curriculum source: COMP1100 Ch. 2 + Ch. 3.

## Required artifacts

| File | Skill |
|---|---|
| `hypothesis-register.md` | `venture-core/hypothesis-register` |
| `bmc-v1.md` | `business-model/bmc-build` (the v1 is *all guesses*) |

## Hypothesis discipline

Every hypothesis must be falsifiable — see
[`../.rules/hypothesis-rules.md`](../.rules/hypothesis-rules.md). The
`hypothesis-falsifiability-check` skill blocks bad statements.

Every hypothesis carries a `status:` (`open` / `accepted` / `refuted` /
`superseded`) that propagates to the relevant BMC cell when it flips.

## The relationship to other phases

- A test card in `02-customer-discovery/test-cards/` references one or
  more hypotheses here.
- A learning card in `02-customer-discovery/learning-cards/` flips a
  hypothesis status here.
- A pivot logged in `07-validation/pivot-refine-log.md` enumerates which
  hypothesis IDs changed.
