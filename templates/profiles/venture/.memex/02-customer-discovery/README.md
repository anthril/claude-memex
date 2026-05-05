---
title: 02 — Customer Discovery
slug: phase-customer-discovery
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 02 — Customer Discovery

Where the venture finds out whether the problems it imagined are real, who
has them, and which sub-set of those people are willing to do something
about it. The longest phase; expect to spend most of pre-MVP time here.

Curriculum source: COMP1100 Ch. 3, *Customer Discovery*.

## Sub-folder structure

```
02-customer-discovery/
├── segments/
│   └── <segment-slug>/
│       ├── README.md           (required — readme-required hook)
│       ├── profile.md          (jobs / pains / gains)
│       ├── interview-guide.md
│       ├── early-adopters.md
│       └── interviews/
│           └── interview-NNN.md   (append-only)
├── test-cards/
│   └── TC-NNN.md
└── learning-cards/
    └── LC-NNN.md
```

## Required artifacts (per segment)

| File | Skill |
|---|---|
| `segments/<slug>/profile.md` | `customer-discovery/customer-profile-build` |
| `segments/<slug>/early-adopters.md` | `customer-discovery/early-adopter-profile` |
| `segments/<slug>/interview-guide.md` | `customer-discovery/interview-guide-build` |
| `segments/<slug>/interviews/interview-NNN.md` | `customer-discovery/interview-log` |

## The blocking gate

`customer-discovery-status` answers the four-question gate (see
[`../.rules/customer-discovery-rules.md`](../.rules/customer-discovery-rules.md))
before any MVP-planning skill will run. Override with `--force` if you
genuinely intend to plan an MVP without the evidence — the override is
logged.
