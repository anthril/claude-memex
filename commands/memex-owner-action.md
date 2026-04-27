---
description: File a new project-owner action (a thing only the project owner can do)
argument-hint: "<title>"
allowed-tools: Read, Write, Bash
---

# /memex:owner-action

File a new project-owner action under `.memex/.project-owner-actions/`. These are concrete, owner-only items: things agents cannot do (file legal documents, sign contracts, register on external platforms, name a real human as data custodian, confirm a payment processor, kick off an external pentest engagement, etc.).

Use this when an agent identifies work that is **blocking downstream engineering** but **cannot be done by an agent**. Filing it makes the blocker visible, gives it an owner, sets a target close date, and lets the docsite + linter surface it alongside open questions.

## Usage

```
/memex:owner-action Confirm payment processor for the LDA participant study
/memex:owner-action File master preregistration on OSF
/memex:owner-action Sign MOU with neuromorphic replication partner
```

## Behaviour

1. Derive a kebab-case slug from the title (lowercase, strip non-alphanumerics, hyphen-join).
2. Target path: `<root>/.project-owner-actions/<slug>.md` where `<root>` is `memex.config.json#/root`.
3. Refuse if the file already exists. Print the existing file's path and its `status:` field.
4. Otherwise write the file using the project-owner-action frontmatter template:

```markdown
---
title: {{title}}
slug: {{slug}}
type: project-owner-action
status: pending
owner: {{project owner name or unassigned}}
created: {{today}}
updated: {{today}}
target_close_date: <YYYY-MM-DD or `<unscheduled>`>
severity: <low | medium | high | critical>
blocks: <comma-separated list of work items / hypotheses / experiments this blocks, or `<none>`>
---

## Why agents can't do this
<One sentence. Examples: "requires a real human signature on the consent form"; "needs a credit card billing relationship with the payment processor"; "OSF account creation needs human verification"; "naming an independent ethics contact is a personnel decision".>

## What needs to happen
<Concrete description of the action. Specific enough that the project owner can read it cold and know what to do.>

## What this blocks
<Downstream work waiting on this action. Use markdown links to the affected ADRs / preregistrations / experiments / hypotheses.>

- [<short label>](<relative/path>) — <one-line why this is blocked>

## Steps for the project owner
1. <Concrete step>
2. <Concrete step>
3. <How to verify the action is complete>

## Related files
<Same convention as open-questions: markdown links to every page the action touches. Bare paths do not register in the docsite link graph.>

- [<short label>](<relative/path/to/file.md>) — <one-line why this file is relevant>

## Resolution log
<Append-only. When the project owner reports progress, add a dated entry. When complete, append a final entry naming the artefact / OSF URL / signed document and move the file to `.project-owner-actions/.completed/`.>

- {{today}} — filed by Claude.
```

5. Print the created file path and offer to add a link to it from `index.md` under the `## Project-owner actions` section.

Use the frontmatter template from `templates/shared/frontmatter.md.tmpl` for consistency. Owner field defaults to `unassigned` but should be filled with the actual project owner's name as soon as known.

## Required: populate `## What this blocks`

This section is **mandatory**. If the action blocks nothing, it doesn't belong here — it belongs in a personal todo or never. Project-owner actions live in the wiki precisely because they hold up engineering. List the downstream work as markdown links so the wiki link graph surfaces the dependency.

## When to file this vs an open question

| You're filing | Use |
|---|---|
| A decision the team needs to make (multiple defensible options) | `.open-questions/` (`/memex:open-q`) |
| A thing only a real human can do (signatures, accounts, MOUs, money) | `.project-owner-actions/` (`/memex:owner-action`) |
| An engineering task that's just unscheduled | A normal plan file or todo |
| A research-process artefact with TBD fields | The artefact itself, not a separate file |

If you find yourself filing a "project-owner action" whose body is "decide whether to use approach A or B" — that's an open question, not an action. Move it.

## Completion

When the project owner reports the action is complete:
1. Append a dated final entry to `## Resolution log` naming the artefact (OSF URL, signed-document path, named-person, etc.).
2. Move the file from `.memex/.project-owner-actions/<slug>.md` to `.memex/.project-owner-actions/.completed/<slug>.md`.
3. Update the downstream blocked items: each one referenced in `## What this blocks` should have its blocker note updated or removed.

The `wiki-lint` skill flags pending project-owner-actions whose `target_close_date` is in the past.
