---
title: 04 — Competitors
slug: phase-competitors
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 04 — Competitors

Competitor map: who else solves this problem, what do they look like,
where are the gaps?

Curriculum source: COMP1100 Ch. 4, *Value Proposition Canvas* (competitor half).

## Sub-folder structure

```
04-competitors/
├── competitor-table.md          (single canonical table)
├── swot/
│   └── <competitor-slug>/README.md   (required — readme-required hook)
├── uvp.md                       (Unique Value Proposition statement)
└── insights.md                  (synthesis)
```

## Required artifacts

| File | Skill |
|---|---|
| `competitor-table.md` | `competitor-analysis/competitor-table-build` |
| `swot/<slug>/README.md` | `competitor-analysis/swot-build` |
| `uvp.md` | `competitor-analysis/uvp-statement` |
| `insights.md` | `competitor-analysis/competitor-insights` |

Each top-N competitor optionally has a shadow BMC produced by
`competitor-bmc-shadow` — that lives under `05-business-model/` because
it's still a BMC.

## SWOT discipline

Strengths and weaknesses are **internal** to the competitor; opportunities
and threats are **external**. The `swot-build` skill enforces this — a
"strength" that's actually an opportunity gets pushed back. See
[curriculum-citations.md](../../../shared/reference/curriculum-citations.md)
Ch. 4 for the exact wording.

## Insights are actionable

`insights.md` is not "things we noticed about competitors." It's "what does
this change in *our* hypotheses?" Every entry should propose a hypothesis
update.
