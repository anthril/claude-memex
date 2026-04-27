---
title: Project-owner actions
slug: project-owner-actions
type: rule
status: active
owner: unassigned
created: 2026-04-27
updated: 2026-04-27
---

# Project-owner actions

Concrete, owner-only blockers. One file per pending action, kebab-case slug. Completed actions move to `.completed/` with a dated final entry in the resolution log naming the artefact (signed document, OSF URL, named-person, etc.).

Use `/memex:owner-action <title>` to file a new one.

In research-project, project-owner actions typically arise from:

- **Ethics-protocol gates** — naming a real data custodian, naming an independent ethics contact, finalising the consent-form text, confirming a payment processor for participant compensation.
- **Preregistration filing** — creating an OSF account, filing the master preregistration, recording the `preregistration_id`.
- **Replication MOUs** — signing memoranda of understanding with academic / neuromorphic / contractor partners (for the H1, H3, H6 replication commitment).
- **External engagements** — commissioning a pentest team for the safety-sandbox red-team suite, contracting an IRB-approved coding house, paying for a third-party benchmark license.
- **IRB / regulatory** — submitting and securing IRB approval for human studies; recording the approval number.
- **Money** — anything that needs a credit card, an invoice, a budget approval, or a vendor relationship.

## Why this category exists separately from open questions

| You're filing | Use |
|---|---|
| A decision the team needs to make (multiple defensible options) | `.open-questions/` (`/memex:open-q`) |
| A thing only a real human can do (signatures, accounts, MOUs, money) | `.project-owner-actions/` (`/memex:owner-action`) |

Open questions resolve when the team picks an answer. Project-owner actions resolve when a real human in the real world performs a real act. Conflating them hides the difference between "we haven't decided" and "we've decided, and we're waiting on the owner".

## Required: link `## What this blocks`

Every project-owner action **must** include a `## What this blocks` section with markdown links to the downstream work waiting on the action — usually preregistrations, ADRs, gym deployments, or experiment runs. Use `[label](relative/path)`; bare paths do not register in the docsite link graph or the wiki-lint pass.

If the action blocks nothing, it doesn't belong here — it belongs in a personal todo or a calendar reminder. Project-owner actions live in the wiki precisely because they hold up engineering.

## Lifecycle

1. **Filing** — agent (or human) creates `<slug>.md` via `/memex:owner-action`. Status: `pending`.
2. **Owner acknowledges** — owner reads, fills in `owner` field with their name, sets a realistic `target_close_date`, may bump `severity`.
3. **In progress** — owner updates the resolution log with progress entries; status becomes `in-progress`.
4. **Completed** — owner adds a final dated entry to the resolution log naming the artefact / URL / signed document; moves the file to `.completed/`. Each downstream item in `## What this blocks` should be re-checked.
5. **Cancelled** — if the action becomes moot (downstream work was scoped out, etc.), status becomes `cancelled` and a final log entry explains why; the file moves to `.completed/`.

## Surfaces

- The `wiki-lint` skill flags pending actions whose `target_close_date` is in the past.
- The `stop-project-owner-actions-check` hook surfaces pending + overdue counts at the end of every session.
- The docsite (when running) renders `.project-owner-actions/` as a top-level section so the owner can see the queue at a glance.
