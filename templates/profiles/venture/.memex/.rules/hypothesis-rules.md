---
title: Hypothesis rules (Ch. 5)
slug: hypothesis-rules
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Hypothesis rules

Curriculum source: COMP1100/COMP7110 Ch. 5, *Experimentation*. The
`hypothesis-falsifiability-check` skill enforces this rule. Override with
`--force`; override is logged automatically.

## A hypothesis must be falsifiable

State what observation would refute it. The three failure modes:

| Failure mode | Example | Fix |
|---|---|---|
| **Too vague** | "Users will love the product" | Replace with a specific behaviour: "≥ 30% of trial users invite a teammate within 7 days" |
| **No measurement** | "The market is big" | Specify the measurement and where the data comes from: "≥ 100k matching businesses on the ABS register" |
| **No decision rule** | "Most early adopters will pay $X" | Specify the threshold and the action it triggers: "If ≥ 60% of segment-A adopters pay $X within 14 days, proceed; if < 60%, refine pricing" |

## Required structure

Every hypothesis in `01-hypotheses/hypothesis-register.md` (or in a test
card) must have:

```markdown
- ID: H-NNN
- Cell: <BMC cell or "cross-cutting">
- Statement: We believe <what>
- Falsifier: We are wrong if <observation>
- Measurement: <how we measure>
- Threshold: <pass/fail line>
- Timeframe: <when we decide>
- Status: open | accepted | refuted | superseded
- Evidence: <links to interviews / test cards / learning cards>
- Updated: YYYY-MM-DD
```

If any of `Falsifier`, `Measurement`, `Threshold`, `Timeframe` are missing,
the falsifiability check refuses.

## Status transitions

| From | To | Trigger |
|---|---|---|
| `open` | `accepted` | Learning card with evidence above threshold within timeframe |
| `open` | `refuted` | Learning card with evidence below threshold within timeframe |
| `open` | `superseded` | A new hypothesis replaces this one (link forward) |
| `accepted` | `refuted` | New evidence changes the conclusion (rare; bumps the related BMC version) |
| any | `deprecated` | Pivot: this whole line of inquiry is no longer relevant |

Never silently delete a hypothesis. Set status, link forward, keep the
history.

## Hypothesis vs test card vs learning card

- **Hypothesis** lives in `01-hypotheses/hypothesis-register.md`. Long-lived.
- **Test card** lives in `02-customer-discovery/test-cards/TC-NNN.md`. One
  per experiment. References the hypothesis it tests.
- **Learning card** lives in `02-customer-discovery/learning-cards/LC-NNN.md`.
  One per concluded test. References both the test card and the hypothesis
  it updates.
