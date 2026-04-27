---
title: Open questions
slug: open-questions
type: rule
status: active
owner: unassigned
created: 2026-04-23
updated: 2026-04-27
---

# Open questions

Unresolved cross-cutting items. One file per question, kebab-case slug. Resolved questions move to `.resolved/` with a dated `## Resolution` section.

Use `/memex:open-q <title>` to file a new one.

## Required: link the related files

Every open question **must** include a `## Related files` section with markdown links — `[label](relative/path)` — to every page the question touches: the wiki pages that prompted it, the specs / `raw/` sources whose interpretation hinges on the answer, and any pages whose claims will need updating once the question resolves.

Bare paths or code-fenced filenames do not count — the docsite link graph and the `wiki-lint` skill only pick up real markdown links. If you cannot identify any related file, the item is probably a note that belongs inline on the source's page, not a cross-cutting question.
