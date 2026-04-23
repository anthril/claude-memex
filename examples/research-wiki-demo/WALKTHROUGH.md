# Research-wiki demo — walkthrough

This directory is a **fully-realised** `research-wiki` profile after one `/memex:ingest` pass. Reviewers can diff the `raw/` source against the `wiki/` output to see exactly what the ingest skill produces. This is the concrete answer to "can Memex actually do an end-to-end ingest" — stored in the repo so the contract is verifiable without running the plugin.

## The story

1. **Day 0** — `/memex:init research-wiki` scaffolds the profile. `log.md` gets one entry:
   ```
   ## [2026-04-23] init | research-wiki profile scaffolded
   ```

2. **User drops a source.** `raw/articles/transformer-circuits.md` appears (a fictional composite article for demo purposes).

3. **`/memex:ingest .memex/raw/articles/transformer-circuits.md`.** The `ingest-source` skill fires. What it produces:

   | File | Why |
   |---|---|
   | `wiki/summaries/transformer-circuits.md` | One summary per source (skill step 4) |
   | `wiki/entities/anthropic/README.md` | Entity extracted; first-class organisation (skill step 5) |
   | `wiki/concepts/mechanistic-interpretability/README.md` | Primary methodological concept (skill step 5) |
   | `wiki/concepts/induction-heads/README.md` | Canonical finding, warrants its own page (skill step 5) |
   | `.open-questions/how-does-induction-work-at-scale.md` | Cross-cutting question surfaced by the source (skill step 7) |

4. **`index.md` updated** with 4 new catalogue entries under the relevant sections (skill step 8).

5. **`log.md` appended** with a second entry (skill step 9):
   ```
   ## [2026-04-23] ingest | transformer-circuits
   ```

6. **Cross-references.** Every wiki page links to:
   - The summary it originated from (via `[[transformer-circuits]]`)
   - Related entity/concept pages (via `[[slug]]`)
   - The open question(s) it references

## Contract verification

This directory is checked by `tests/test_demo_ingest.py`:

- Every wiki file has valid frontmatter (`frontmatter-check` passes)
- Every path is kebab-case (`path-guard` passes)
- The summary links back to all entity/concept pages it extracted
- Every entity/concept page links back to the originating summary
- The index references every wiki page
- The log has a parseable ingest entry

If you're editing the ingest skill (`skills/ingest-source/SKILL.md`), update this demo too so the contract stays in sync.

## How to read this directory

- Start with [`.memex/raw/articles/transformer-circuits.md`](.memex/raw/articles/transformer-circuits.md) — the source
- Then [`.memex/wiki/summaries/transformer-circuits.md`](.memex/wiki/summaries/transformer-circuits.md) — what Memex produced as the canonical summary
- Then the 3 entity/concept pages — observe how each links back to the summary and to each other
- Finally [`.memex/index.md`](.memex/index.md) and [`.memex/log.md`](.memex/log.md) — the navigation/history layer

## Not for use

This folder is illustrative. Don't import it, clone from it, or treat it as a library.
