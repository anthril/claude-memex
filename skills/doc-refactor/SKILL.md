---
name: doc-refactor
description: Structurally refactor wiki pages — split a page into multiple, merge two or more into one, rename a slug across all references. Handles cross-reference updates automatically. Invoked when the user says "split this page", "merge these pages", "rename this slug", or "refactor the wiki".
triggers:
  - "split this page"
  - "merge these pages"
  - "rename this slug"
  - "refactor the wiki"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Refactor wiki pages

Three supported operations. Confirm the operation with the user before executing — structural edits are high-blast-radius.

## Split a page

Inputs: source page path, the new slug(s) + what-belongs-where guidance from the user.

1. Read the source page in full
2. Confirm with the user which sections go into which new page
3. Create each new page with full frontmatter (inheriting `owner:`, `status:`, `type:` from the source where sensible)
4. Rewrite the source page as a stub linking to the new pages, OR delete it if the user prefers
5. Find all inbound links to the source (`Grep` across ops root) — update each to point at the new page(s) they most logically reference. When ambiguous, ask the user
6. Update `index.md`
7. Append `log.md` with `event: refactor-split | <source-slug>`

## Merge pages

Inputs: two or more source pages + the target slug + the user's guidance on ordering / deduplication.

1. Read each source page
2. Draft the merged page: combine bodies, deduplicate claims, preserve the union of cross-references, keep a merged `## Changelog` if sources had one
3. Frontmatter: new `created:` = earliest of the sources; `updated:` = today; merge `owner:` manually if different
4. Write the target page
5. Replace each source page with a stub `# Moved → [new-slug](new-slug.md)` that is deleted after outbound link updates (or delete sources immediately — user's choice)
6. Update inbound links to sources → point at the target
7. Update `index.md` (remove old entries, add new)
8. Append `log.md` with `event: refactor-merge | <target-slug> (from <n> sources)`

## Rename a slug

Inputs: old slug, new slug.

1. Validate that the new slug is kebab-case and unique
2. Rename the file/folder on disk
3. Update the page's frontmatter `slug:` field
4. `Grep` all `[link](path)` and `[[slug]]` references across the ops root — update each
5. Update `index.md`
6. Append `log.md` with `event: refactor-rename | <old> → <new>`

## Guardrails

- Never execute a refactor without confirming the scope with the user
- Always bump `updated:` on every touched page
- If a referencing page has a `## Changelog`, append a note: `renamed <old> → <new>` on YYYY-MM-DD
- If the user hasn't committed recent changes, warn them before starting — refactors have wide blast radius
- If the wiki is large (>50 pages) prefer running as the `memex-linter` subagent in worktree isolation so the main session doesn't inherit the churn
- If `memex-docsite serve` is running, refactored URLs may break readers' open tabs — call out renames in the user-facing summary so they can refresh
