---
title: Project owner actions
slug: project-owner-actions
type: rule
status: active
owner: unassigned
created: 2026-05-05
updated: 2026-05-05
---

# Project owner actions

Owner-only blockers — things only the human founder can resolve. The agent
files them here and surfaces them at session start, but never silently
clears them.

In ventures, common owner actions include:

- **Legal / IP** — trademark check, IP assignment, terms of service review,
  privacy policy approval
- **Regulatory** — industry-specific licensing, ethics signoff, accessibility
  certification, data-protection registration
- **MOUs and partner agreements** — signed letters of intent from
  earlyvangelists, channel partner contracts, supplier MOUs
- **Payment processor** — Stripe/Square/PayPal account confirmation, ABN
  registration, GST setup
- **Domain and brand** — register the domain, secure social handles, file
  trade mark
- **Corporate setup** — entity formation, bank account, accounting setup

Use `/memex:owner-action <title>` to file a new one.

Each file has the shape:

```markdown
---
title: <human-readable title>
slug: <kebab-case>
type: open-question
status: draft|active|deprecated|superseded
owner: <who can resolve this>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <title>

## Why this is owner-only
What about this requires the human, not the agent? (Legal authority,
account ownership, regulatory standing, signature power.)

## What's needed
The specific action and any preconditions (documents, accounts, fees).

## Blocks
- [What this blocks](path/to/blocked/page.md) — what work can't proceed
  until this is done.

## Suggested vendor / pathway
If applicable, the cheapest / fastest way to complete it.
```

## Resolved actions

Move resolved actions to `.resolved/<YYYY-MM-DD>-<slug>.md` with a
`## Resolution` section. Don't delete — preserve the audit trail.
