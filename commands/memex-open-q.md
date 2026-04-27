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

## Related files
<Markdown links to every file the question touches: pages that informed it, specs/code/configs whose interpretation hinges on the answer, and any docs the resolution will need to update. Use real paths so the wiki link graph captures them; bare paths (no `[]()`) do not count.>

- [<short label>](<relative/path/to/file.md>) — <one-line why this file is relevant>
- ...

## What we know
- <dot point>

## What we'd need to decide
- <dot point>

## Proposed resolutions
1. <alternative with tradeoff>
```

5. Print the created file path and offer to add a link to it from `index.md` under the `## Open Questions` section.

Use the frontmatter template from `templates/shared/frontmatter.md.tmpl` for consistency. All required fields must be filled — an empty `owner` (default `unassigned`) is acceptable at creation, but populate it on the first non-trivial edit.

## Required: populate `## Related files`

This section is **mandatory** — never leave it empty or as a placeholder. Before writing the file:

- Identify every page that prompted, references, or will be updated by the question (re-read the calling session's recent context, the wiki pages cited, and the `raw/` source if applicable).
- Write each entry as a markdown link `[label](relative/path)` so the wiki link graph and the docsite's `/graph` view pick it up. The `wiki-lint` skill flags open questions whose `## Related files` is missing or contains bare paths.
- Order: most-affected pages first; downstream pages after.
- If the question is genuinely cross-cutting and touches many pages, link the parent index pages (e.g. `architecture/engineering-spec/index.md`) rather than enumerating dozens.
- If you truly cannot identify any related file, the question probably belongs in a parent doc as a note, not in `.open-questions/` — reconsider before filing.
