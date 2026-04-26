---
name: ingest-source
description: Ingest a raw source into the Memex wiki. Reads the file, summarises it to a new page under the profile's summary folder, extracts entities/concepts/topics and updates or creates their pages, bumps index.md, appends log.md. Invoked when the user mentions ingesting an article, processing a source, or adding a file under .memex/raw/ to the wiki.
triggers:
  - "ingest this"
  - "process this article"
  - "add this to the wiki"
  - "read this and update the wiki"
  - any user message containing a path under `.memex/raw/`
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Ingest a source into the Memex wiki

A single ingest can touch 10–15 pages. Work through the list below in order; skip steps that don't apply to the current profile. The profile is declared in `memex.config.json#/profile`.

## 1. Load context

- Read `memex.config.json` to identify `root`, `profile`, `readmeRequired`, and the frontmatter schema
- Read `.memex/index.md` and `.memex/log.md` head
- If the source path is not yet under `.memex/raw/` (for research-wiki) or not yet located in the project, ask the user where the file lives before proceeding

## 2. Read the source

- Read the source file in full — do not skim
- If the source exceeds 20k chars, read the whole thing anyway (it's the ingest) but summarise in chunks

## 3. Discuss key takeaways

Before writing anything, briefly discuss with the user:

- What the source is about in 2–3 sentences
- The 3–5 concrete claims / takeaways
- Entities, concepts, or topics mentioned that are candidates for page creation

Ask the user to confirm or redirect before writing. This is the most valuable human-in-the-loop step.

## 4. Write the summary page

Target folder per profile:

| Profile | Summary path |
|---|---|
| `research-wiki` | `wiki/summaries/<source-slug>.md` |
| `research-project` | `wiki/summaries/<source-slug>.md` |
| `engineering-ops` | `.research/<DDMMYYYY-HHMM>/<source-slug>.md` |
| `book-companion` | `wiki/summaries/<chapter-or-source-slug>.md` |
| `personal-journal` | `wiki/topics/<derived-topic>/<source-slug>.md` |
| `generic` | `topics/<derived-topic>/<source-slug>.md` |

The summary page MUST carry full frontmatter per `frontmatter.required`. Body sections:

```markdown
# {{title}}

## Source
<citation — URL, author, date, where it lives locally>

## TL;DR
<2–3 sentence summary>

## Key claims
- <dot point with page/section reference if the source has them>

## Entities and concepts mentioned
- [[entity-slug]] — brief note on context
- [[concept-slug]] — brief note on context

## Connections to existing pages
- <where this reinforces, contradicts, or extends the existing wiki>

## Open questions raised
- <question → filed to `.open-questions/<slug>.md` in step 7 if cross-cutting>
```

## 5. Extract entities and concepts

For each named entity or concept:

1. Check if a page already exists (`Grep` the ops root for the slug, then `Read` any hits)
2. If YES → update that page with the new information. Bump `updated:`. Append to a `## Recent additions` section with the date and source citation. Note any contradictions prominently.
3. If NO → create a new page using the profile's convention (`wiki/entities/<slug>.md`, `wiki/concepts/<slug>.md`, `entities/<slug>/README.md`, etc.). Full frontmatter. Body minimum: what this thing is, where it was first encountered, initial key facts.

## 6. Update cross-references

For every page you created or edited in step 5:

- Ensure it links to the new summary page (`[[source-slug]]`)
- Ensure the summary page links to it
- If two pages now share an entity that they didn't reference before, add the cross-link both ways

## 7. File cross-cutting open questions

Any question from step 3 that doesn't cleanly belong to one page → file as `.open-questions/<slug>.md` using the open-question template (frontmatter + `## Context / ## The question / ## What we know / ## What we'd need to decide`).

## 8. Update index.md

- Add the new summary page under the appropriate section
- Add any new entity/concept pages under their sections
- Keep `Recent Activity` or equivalent up to date

## 9. Append log.md

Entry using the profile's `log.entryPrefix` template:

```
## [YYYY-MM-DD] ingest | <source title or slug>
```

Body (optional but recommended):

- Files created: list
- Files updated: list
- Notable contradictions flagged: list
- Open questions raised: list

## 10. Close out

- Present the diff summary to the user (files created / updated / touched)
- Flag anything surprising or that needs their decision
- If you created any stub pages (entities/concepts mentioned but not yet researched), list them as candidates for future investigation
- If `memex-docsite serve` is running, the new pages appear at `/<slug>/` immediately and surface in the appropriate `/sections/<type>/` listing (5-second graph cache)
