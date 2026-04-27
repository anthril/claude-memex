---
name: wiki-lint
description: Health-check the Memex wiki. Find orphan pages, contradictions, stale claims, missing cross-references, pages referenced but missing, overdue open questions, and data gaps. Produce a report; offer to auto-fix easy issues. Invoked when the user says "lint the wiki", "audit my docs", "health-check the wiki", or runs /memex:lint.
triggers:
  - "lint the wiki"
  - "audit my docs"
  - "health-check the wiki"
  - "run wiki-lint"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Lint the Memex wiki

Produces a structured findings report. Each finding has a severity (`info`, `warn`, `issue`), a path, and a one-line description. Offer auto-fix for the trivially mechanical ones.

## 1. Enumerate pages

- Glob `<ops-root>/**/*.md`
- Exclude `<ops-root>/.state/**`
- Parse frontmatter on each file

## 2. Check frontmatter

- Missing required fields → `issue`
- `status: deprecated` pages still referenced elsewhere → `warn`
- `updated:` older than 180 days with `status: active` → `warn` (stale claim candidate)
- Inconsistent `owner:` formats → `info`

## 3. Build a link graph

- For every markdown link `[...](path.md)` or wikilink `[[slug]]`, record the from→to edge
- Note which pages are referenced but don't exist (dangling links) → `issue`
- Note pages with zero inbound links (orphans) → `warn`
- Note pages with a single inbound from the index (otherwise orphan) → `info`

> **Cross-check against the docsite.** When `memex-docsite serve` is running locally, `GET /api/graph` returns the same orphan / hub / dead-end sets — built from the same wikilink regex. Diverging answers usually mean the lint scope and the docsite's `is_ignored` patterns disagree.

## 4. Scan for contradictions

- Pages that mention the same entity with different `status:`, `category:`, or framework field values → `warn` (surface both and let the user decide)
- Numeric claims about the same thing with different numbers → `issue`

## 5. Check index and log

- Every wiki page listed in `index.md`? Missing → `warn`
- `log.md` entries use the parseable prefix? Malformed prefixes → `info`
- Entries in the last 30 days? No entries → `info` ("wiki looks dormant")

## 6. Check open questions

- Every `.open-questions/*.md` has an `owner:` set (not `unassigned`)? Unassigned → `warn` if age > 30 days
- Resolved questions in `.open-questions/` (not yet moved to `.resolved/`) → `info`
- Every active `.open-questions/*.md` has a populated **related-files section**:
  - The section is named `## Related files` (slash-command template) **or** is the `## Scope > Affected wiki areas` bullet block (elaborate template). One of the two MUST be present.
  - The section MUST contain at least one markdown link `[label](path)`. Bare paths, code-fenced filenames, or empty placeholders (`<...>`) → `issue`.
  - Each linked path MUST resolve to an existing file (relative to the open question's directory). Dangling target → `issue`.
  - Section absent entirely → `issue`.
- Resolved-by-ADR convention: a question with `status: resolved-by-ADR-NNNN` should have a corresponding `## Resolution log` entry citing the ADR by number → missing entry → `warn`.

## 7. Check code-to-doc mappings

For every entry in `memex.config.json#/codeToDocMapping`:

- Glob the code pattern. For each match, check the required doc exists → missing → `issue`
- For every doc referenced, check the code still exists → missing → `warn` (doc has outlived its code)

## 8. Report

Group findings by severity. Print table with columns: severity | path | finding.

Summary line: `N issues, M warnings, K info`.

## 9. Offer auto-fixes

For each of these, offer to fix:

- **Missing index entry** — append to the appropriate section of `index.md`
- **Orphan page** — offer to add a "See also" link from the most plausible parent
- **`updated:` bump needed** on a page you're about to edit — bump it
- **Dangling link** — offer to create a stub page OR remove the link
- **Open question with bare-path related-files** — offer to convert each bare path to a `[label](path)` markdown link. Derive the label from the file's `title:` frontmatter where possible.

Do NOT auto-resolve contradictions, stale-claim warnings, or empty-related-files findings — those need human judgement (the agent has to decide which files actually relate to the question).

## 10. Save the report

Offer to write the report to `<ops-root>/.audits/<DDMMYYYY-HHMM>/lint-report.md`. Useful trend data for subsequent lints.
