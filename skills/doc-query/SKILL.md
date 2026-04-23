---
name: doc-query
description: Answer a question using the Memex wiki. Read the index, find relevant pages, read them, synthesise a cited answer, optionally file the answer back as a new wiki page for compounding value. Invoked when the user asks a question referring to "the wiki", "my notes", "the docs", or asks a question whose answer likely lives in the wiki.
triggers:
  - "what does the wiki say about"
  - "based on my notes"
  - "check the docs for"
  - "search the wiki"
  - "synthesise from the wiki"
allowed-tools: Read, Write, Grep, Glob, Bash
---

# Query the Memex wiki

## 1. Load index

- Read `memex.config.json#/index.path` (default `index.md`) under the ops root
- Scan for sections relevant to the question

## 2. Search

- If `search.engine` is `qmd` and `qmd` is on PATH, shell out: `qmd search --path <ops-root> --top 8 -- "<question>"`
- Otherwise, use `Grep` across the ops root with keywords from the question (drop stopwords)
- Collect up to 8 candidate pages

## 3. Read

- Read the top candidate pages in full (not chunks)
- Note the frontmatter `updated:` date — if stale, flag it

## 4. Synthesise

Draft an answer with:

- A direct response in 1–3 paragraphs
- Citations as inline links — `[page-title](<root>/<path>.md)` — for every claim
- A short `## Caveats` section noting where the wiki is thin, stale, or contradictory on this topic
- A `## Next steps` section suggesting what to investigate or ingest to sharpen the answer

## 5. Offer to file the answer back

Ask the user: "Would you like me to file this as `<root>/wiki/analyses/<slug>.md` so it compounds?"

If yes:

- Write the analysis page with full frontmatter (`type: analysis` or equivalent)
- Cross-link to every page cited
- Update `index.md` under the appropriate analyses / syntheses section
- Append a `log.md` entry with `event: query | <question snippet>`

## 6. Handle no-match

If nothing relevant is found:

- Say so directly — don't manufacture an answer from training data
- Suggest which `raw/` or external source might fill the gap
- Offer to file the question as `.open-questions/<slug>.md`
