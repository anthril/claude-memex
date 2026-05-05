---
title: 06 — Relationships and Channels
slug: phase-relationships-channels
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# 06 — Relationships and Channels

How we get, keep, and grow customers, and the channels through which we
reach them.

Curriculum source: COMP1100 Ch. 8, *Customer Relationships & Channels*.

## Required artifacts

| File | Skill |
|---|---|
| `get-keep-grow.md` | `relationships-channels/get-keep-grow-design` |
| `channel-strategy.md` | `relationships-channels/channel-select` + `relationships-channels/product-channel-fit-check` |
| `funnel-model.md` | `relationships-channels/funnel-model` |
| `churn-model.md` | `relationships-channels/churn-model` |

## Get / keep / grow

Three stages, three different metrics, often three different
investments. The skill walks each stage explicitly so they don't get
collapsed.

## Direct vs indirect channels

Each candidate channel is classified:

- **Direct**: we own the customer relationship (website, app, retail
  store, sales team)
- **Indirect**: a partner does (resellers, marketplaces, affiliates)

Product-channel fit (`product-channel-fit-check`) asks: is this channel
coherent with this product? SaaS sold via retail is incoherent. A mass-
market consumer good sold by inside sales is incoherent. Mismatches are
flagged.

## Funnel and churn

`funnel-model` builds a quantitative funnel (visitors → signups →
activations → paid → retained). `churn-model` projects remaining customers
after `n` periods at retention rate `r` using `(1 − r)^n`, and average
customer lifetime as `1/(1 − r)`.

These hand off to `mvp-planning/funnel-instrumentation-spec` once the MVP
is being built — that translates the funnel into events the engineers
instrument.
