---
title: 05 — Business Model
slug: phase-business-model
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 05 — Business Model

Business Model Canvas, versioned. Each version snapshots the venture's
current understanding; hypothesis flips drive new versions.

Curriculum source: COMP1100 Ch. 2, *Business Model Canvas*.

## Required artifacts

| File | Skill |
|---|---|
| `bmc-vN.md` | `business-model/bmc-build` (initial), `business-model/bmc-update` (subsequent) |

`bmc-v1.md` lives in `01-hypotheses/` because v1 is "all guesses." From v2
onward, BMCs land here.

## BMC versioning rules

A new version is required when:

- A hypothesis flips from `open` to `accepted`/`refuted` and changes a cell
- A pivot happens (per [`../.rules/pivot-refine-rules.md`](../.rules/pivot-refine-rules.md))
- The customer-segments cell changes (this almost always cascades)

The `bmc-update` skill handles the diff and version bump; old versions get
`status: superseded` with a forward link.

## Cell tagging

Every cell entry is tagged `hypothesis` or `fact`. A cell starts as
`hypothesis` and only becomes `fact` once a learning card with sufficient
evidence flips it.

## Front-stage / back-stage

`bmc-front-back-split` produces a derived view:

- **Front-stage** (right side): customer segments, value propositions,
  channels, customer relationships, revenue streams
- **Back-stage** (left side): key activities, key resources, key partners,
  cost structure

Useful for sequencing work — front-stage hypotheses tend to be cheaper to
test.
