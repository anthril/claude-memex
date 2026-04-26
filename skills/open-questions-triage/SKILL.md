---
name: open-questions-triage
description: Triage the open questions backlog. Group by topic, flag overdue items, propose resolutions or promotions, offer to move resolved items to .resolved/. Invoked when the user says "triage open questions", "what's blocking me", or "review the open questions list".
triggers:
  - "triage open questions"
  - "what's blocking me"
  - "review open questions"
  - "resolve open questions"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Triage open questions

## 1. Enumerate

- Glob `<ops-root>/.open-questions/*.md` (exclude `.resolved/`)
- Parse frontmatter — capture `title`, `slug`, `status`, `owner`, `created`, `updated`
- A page with `status: resolved` in its frontmatter is treated as resolved even if it hasn't been moved to `.resolved/` (matches docsite behaviour as of 0.1.0a2).

> **Note.** The docsite's `/open-questions` view lists the same files. Browser-driven submissions land in this same folder and append a line to `log.md`, so a triage pass and a docsite browse are looking at the same data.

## 2. Group

Group the list by:

- Age bucket: `<1 week`, `1–4 weeks`, `1–3 months`, `3+ months`
- Owner (unassigned last)
- Topic — infer from the slug / title / `## Context` paragraph

## 3. Flag

- `owner: unassigned` AND age > 2 weeks → flag as needs-owner
- `status: open` AND age > 90 days → flag as overdue
- Any `TODO`/`TBD` markers inside the question body → surface them

## 4. Present

Present the triage as a table. Columns: slug | title | age | owner | flags.

Group by age bucket, newest first within each.

## 5. Propose actions

For each overdue or overlong question, propose one of:

- **Resolve now** — if the wiki has accumulated enough context to answer it. Offer to add `## Resolution` with date and move to `.resolved/`
- **Split** — if the question is too broad. Offer to create sub-questions
- **Demote** — if it's no longer relevant. Offer to move to `.resolved/` with resolution = "no longer applicable"
- **Escalate** — if resolving requires a decision outside the wiki. Leave the question and tag the owner (bump `updated:` to now)
- **Promote to doc** — if the answer is substantive enough to become a page. Offer to create `entities/<slug>/README.md` or similar, then mark the open question resolved with a link to the new page

## 6. Execute the user's choices

Carry out the actions one by one. Each action:

- Edits the question file (bumps `updated:`)
- May move the file to `.resolved/` (use `git mv` if available, else filesystem move)
- Appends a `log.md` entry with `event: open-q-resolved | <slug>`

## 7. Report

Summary: how many questions were reviewed, how many resolved / split / demoted / escalated / promoted. Flag any remaining needs-owner items.
