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

Project-owner actions are things an agent **cannot** do: sign a contract, register on an external platform, name a real human as data custodian, confirm a payment processor, kick off an external engagement, file a regulatory submission. They block downstream work, so they belong in the wiki — not in a personal todo list.

## Open question vs project-owner action

| You're filing | Use |
|---|---|
| A decision the team needs to make (multiple defensible options) | `.open-questions/` (`/memex:open-q`) |
| A thing only a real human can do (signatures, accounts, MOUs, money) | `.project-owner-actions/` (`/memex:owner-action`) |

Open questions resolve when the team picks an answer. Project-owner actions resolve when a real human performs a real act.

## Required: link `## What this blocks`

Every project-owner action must list the downstream work it blocks as markdown links. If it blocks nothing, it doesn't belong here.

## Lifecycle

`pending → in-progress → completed | cancelled`. Completed and cancelled files move to `.completed/`. The session-stop hook surfaces pending + overdue counts every time you finish a session.
