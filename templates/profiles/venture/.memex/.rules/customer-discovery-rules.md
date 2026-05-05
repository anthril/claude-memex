---
title: Customer-discovery rules (Ch. 3)
slug: customer-discovery-rules
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Customer-discovery rules

Curriculum source: COMP1100/COMP7110 Ch. 3, *Customer Discovery*. The
`customer-discovery-status` skill enforces this gate. Override with
`--force`; override is logged automatically.

## The four-question gate

Before a venture can move into MVP planning, the four discovery questions
must each return a confident **yes**:

1. **Have we found a problem people care about?**
   - Evidence: ≥ 5 interviews per primary segment, with the same problem
     surfacing unprompted in ≥ 60% of them.
2. **Have we got the right segment?**
   - Evidence: a written `customer-profile.md` that prioritises jobs/pains/
     gains, plus a written `early-adopters.md` matching the Ch. 3 five
     criteria.
3. **Have we got the right early adopters?**
   - Evidence: ≥ 3 named earlyvangelists per primary segment with contact
     details, who have engaged at least twice (interview + follow-up).
4. **Are they willing to engage?**
   - Evidence: ≥ 1 commitment per segment from an earlyvangelist —
     pre-order, LOI, sign-up, payment, scheduled deep-dive call. The
     learning-card record is the receipt.

## What "evidence" means

The gate checks artifacts in the venture tree:

| Question | Files checked |
|---|---|
| Q1 | Aggregated count of segment-tagged interviews; pattern frequency from `interview-summary.md` per segment |
| Q2 | Existence and `status: active` of `02-customer-discovery/segments/<slug>/profile.md` |
| Q3 | Existence and `status: active` of `02-customer-discovery/segments/<slug>/early-adopters.md` with ≥ 3 named entries |
| Q4 | Learning cards with status `accepted` whose evidence is a paid pre-order, LOI, or signed call |

If a check fails, `customer-discovery-status` returns RAG-style readiness:

- 🟢 **Ready** — all four questions pass; MVP planning may proceed
- 🟡 **Partial** — some pass; print which fail and what evidence is needed
- 🔴 **Not ready** — fundamentals missing; skills that depend on Q1-Q4
  refuse to run

## Users vs paying customers

Distinguish them in the segment profile:

- **User**: uses the product
- **Paying customer**: pays for it

They are not always the same person. A B2B SaaS user is rarely the buyer.
Run discovery on both. The segment profile must declare which is which.

## Interview quality bar

Interviews must:

- Be ≤ 30 minutes
- Use open questions only ("What do you do when X?" not "Would you use Y?")
- Ask "Why?" follow-ups
- Ask "Why not?" once a stated preference exists
- Ask "Who else should we talk to?" near the end
- Ask "Can we follow up?" before closing

The `interview-guide-build` skill prefills this structure. Logged interviews
are append-only — see [`AGENTS.md`](../AGENTS.md) §7.
