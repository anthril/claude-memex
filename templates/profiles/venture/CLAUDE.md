# {{ProjectName}} — Claude Instructions

A venture managed by [Memex](https://github.com/anthril/claude-memex)
(`venture` profile). The venture profile turns the COMP1100/COMP7110
*Introduction to Software Innovation* curriculum into a structured tree:
vision → hypotheses → customer discovery → VPC → competitor map → BMC →
relationships and channels → validation → prototype → MVP plan.

## Agent contract

See [.memex/AGENTS.md](.memex/AGENTS.md). Core rule: the LLM authors and
maintains the venture wiki; the human runs interviews, makes pivot/refine
decisions, and approves connector mutations.

## How to drive this venture

The marketplace [`@anthril/startup-factory`](https://github.com/anthril/startup-factory)
ships nine plugins — `venture-core`, `customer-discovery`,
`value-proposition`, `competitor-analysis`, `business-model`,
`experimentation`, `relationships-channels`, `prototyping`, `mvp-planning` —
that drive the customer-development loop on top of this profile.

The numeric prefixes (`00-vision/` through `09-mvp/`) encode the
customer-development sequence. `phase-router` reads the index to decide
"where you are."

## Key indices

- [.memex/README.md](.memex/README.md) — folder map
- [.memex/index.md](.memex/index.md) — page catalogue
- [.memex/log.md](.memex/log.md) — chronological ledger
- [.memex/.open-questions/](.memex/.open-questions/) — unresolved items
- [.memex/.project-owner-actions/](.memex/.project-owner-actions/) — owner-only blockers
- [.memex/.rules/](.memex/.rules/) — venture conventions and curriculum gates

## Three blocking gates

This profile encodes three opinions as guard-rails. Override with `--force`
on the relevant skill if you really mean it; the override gets logged to
`log.md`:

1. **Hypothesis falsifiability** — every hypothesis must be testable
   (`hypothesis-rules.md`)
2. **Customer-discovery readiness** — four questions must return yes before
   MVP work (`customer-discovery-rules.md`)
3. **Prototype vs MVP** — artifacts can't be mislabeled
   (`prototype-vs-mvp-rules.md`)

## Desktop app

This venture is also viewable in the [`@anthril/memex`](https://github.com/anthril/memex)
desktop app — graph view across segments, hypotheses, VPCs and BMC cells, plus
BM25 search via tantivy.

## Project-specific additions

<!-- Put project-specific Claude instructions here. -->
