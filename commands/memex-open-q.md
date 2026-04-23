---
description: File a new open question
argument-hint: "<title>"
allowed-tools: Read, Write, Bash
---

# /memex:open-q

File a new cross-cutting open question under `.memex/.open-questions/`.

## Usage

```
/memex:open-q What happens to in-flight webhooks during a deploy?
```

## Behaviour

1. Derive a kebab-case slug from the title (lowercase, strip non-alphanumerics, hyphen-join).
2. Target path: `<root>/.open-questions/<slug>.md` where `<root>` is `memex.config.json#/root`.
3. Refuse if the file already exists. Print the existing file's path and its `status:` field.
4. Otherwise write the file using the open-question frontmatter template:

```markdown
---
title: {{title}}
slug: {{slug}}
type: open-question
status: open
owner: unassigned
created: {{today}}
updated: {{today}}
---

## Context
<What prompted this question. Link the page / audit / session.>

## The question
{{title}}

## What we know
- <dot point>

## What we'd need to decide
- <dot point>

## Proposed resolutions
1. <alternative with tradeoff>
```

5. Print the created file path and offer to add a link to it from `index.md` under the `## Open Questions` section.

Use the frontmatter template from `templates/shared/frontmatter.md.tmpl` for consistency. All required fields must be filled — an empty `owner` (default `unassigned`) is acceptable at creation, but populate it on the first non-trivial edit.
