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

Concrete, owner-only blockers. One file per pending action, kebab-case slug. Completed actions move to `.completed/` with a dated final entry naming the resolving artefact.

Use `/memex:owner-action <title>` to file a new one.

In engineering-ops, project-owner actions typically arise from:

- **Production credentials** — provisioning a new vault entry, rotating a secret that requires the principal to authorise, registering an OAuth client with a third party.
- **Vendor relationships** — signing an MSA, adding a new SaaS to the procurement list, increasing a quota that needs a credit-card-on-file change.
- **Compliance / regulatory** — SOC2 attestation tasks, data-residency reviews, signing DPAs.
- **Incident response handoff** — when a postmortem identifies an action only a human can take (e.g. notify a customer, file a regulator-required disclosure).
- **Org changes** — naming an on-call captain, designating a security contact, confirming a budget owner for a cost-driver alert.

## Open question vs project-owner action vs incident vs runbook task

| Filing | Use |
|---|---|
| Decision the team needs to make | `.open-questions/` (`/memex:open-q`) |
| Thing only a real human can do | `.project-owner-actions/` (`/memex:owner-action`) |
| Production incident postmortem | `.incidents/` |
| Repeatable on-call procedure | `runbooks/` |

Open questions resolve when the team picks an answer. Project-owner actions resolve when a real human performs a real act in the real world. Postmortems are immutable historical records. Runbooks are how-tos.

## Required: link `## What this blocks`

Every project-owner action must list the downstream work it blocks as markdown links — usually a deploy, a runbook gate, a planning entry, an incident remediation step. If it blocks nothing, it belongs on a personal calendar.

## Lifecycle

`pending → in-progress → completed | cancelled`. Completed and cancelled files move to `.completed/`. The session-stop hook surfaces pending + overdue counts at the end of every session; the docsite renders this folder as a top-level section so the owner sees the queue at a glance.
