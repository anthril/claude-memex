---
title: 03 — Value Proposition
slug: phase-value-proposition
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 03 — Value Proposition

Value Proposition Canvases — one per primary segment, versioned as
customer feedback refines them.

Curriculum source: COMP1100 Ch. 4, *Value Proposition Canvas*.

## Required artifacts

| File | Skill |
|---|---|
| `vpc-<segment>-vN.md` | `value-proposition/value-map-build` (left half), `customer-discovery/customer-profile-build` (right half via segment profile) |

## VPC versioning

A VPC is bumped to v(N+1) when:

- The customer profile (jobs / pains / gains) materially changes
- A pain reliever or gain creator is added or removed
- The fit relationship changes (e.g. a previously-prioritised pain has no
  reliever)

`vpc-version` snapshots and bumps. Old versions are kept (`status:
superseded`) for audit.

## Fit check

`vpc-fit-check` cross-checks that every prioritised pain has at least one
pain reliever and every prioritised gain has at least one gain creator.
A VPC with unmatched pains/gains is `status: draft` until the fit is real.

## The relationship to BMC

Each VPC links to:

- The segment in `02-customer-discovery/segments/<slug>/`
- The current BMC's customer-segments and value-propositions cells
  (`05-business-model/bmc-vN.md`)
