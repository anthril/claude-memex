# Custom profile walkthrough

A worked example of `/memex:init-profile`. The target project is a speculative-fiction novel repo — none of the six built-in profiles fit cleanly, but `book-companion` is the closest starting point.

---

## The project

```
my-novel/
├── drafts/                 # chapters in progress
├── outlines/               # plot outlines, scene breakdowns
├── research/               # world-building research
├── characters/             # character bibles
├── notes/                  # misc scratch
├── manuscript/             # final chapter files
└── README.md
```

Neither `book-companion` (for *reading* a book, not writing one) nor `research-wiki` (pure ingestion) fits. Time for `/memex:init-profile`.

---

## Session transcript

**User:** `/memex:init-profile`

**Claude (skill):** Surveys the repo.

> This looks like a writing project. Top-level folders: `drafts/ outlines/ research/ characters/ notes/ manuscript/`. Marker files: `README.md`. Closest base profile: `book-companion` — same `raw/wiki` split but built for reading, not writing. Continue with `book-companion` as the base, or pick a different one?

**User:** continue with book-companion.

**Claude:** Asks **Q1 — primary purpose**.

**User:** "Writing a speculative-fiction novel; tracking worldbuilding, characters, plot threads, and scene-by-scene outlines."

**Claude:** Asks **Q2 — current phase**.

**User:** active drafting.

**Claude:** Asks **Q3 — adopt existing folders**.

> I see `drafts/ outlines/ research/ characters/ notes/ manuscript/`. Which should become top-level wiki surfaces?

**User selects:** `characters/` (as `wiki/characters/`), `research/` (as `raw/research/`), `outlines/` (as `wiki/outlines/`).

**User skips:** `drafts/ manuscript/ notes/` — those stay outside the wiki.

**Claude:** Asks **Q4 — new surfaces**.

**User:** "Add `wiki/plot-threads/` (same as book-companion) and `wiki/places/` (worldbuilding locations)."

**Claude:** Asks **Q5 — README gating**.

**User:** Yes for `wiki/characters/*`, `wiki/places/*`, `wiki/plot-threads/*`, `wiki/outlines/*`.

**Claude:** Asks **Q6 — code-to-doc mappings**.

**User:** None — this is not a codebase.

---

## Draft taxonomy

**Claude prints:**

```json
{
  "profile": "novel-wiki",
  "allowedTopLevel": [
    "README.md", "AGENTS.md", "index.md", "log.md",
    ".open-questions", ".rules", ".state",
    "raw", "wiki"
  ],
  "readmeRequired": [
    "wiki/characters/*",
    "wiki/places/*",
    "wiki/plot-threads/*",
    "wiki/outlines/*"
  ],
  "frontmatter": {
    "required": ["title", "slug", "type", "status", "created", "updated"],
    "enum": {
      "type": ["character", "place", "plot-thread", "outline", "summary", "research-note", "open-question", "rule"],
      "status": ["draft", "active", "deprecated"]
    }
  },
  "index": {
    "sections": ["Characters", "Places", "Plot Threads", "Outlines", "Research", "Open Questions", "Recent Activity"]
  }
}
```

Folder tree:

```
.memex/
├── README.md  AGENTS.md  index.md  log.md
├── .open-questions/  .rules/  .state/
├── raw/
│   └── research/           # mirrors top-level `research/` folder via symlink or copy
└── wiki/
    ├── characters/         # one folder per character, README-gated
    ├── places/             # one folder per location, README-gated
    ├── plot-threads/       # one folder per plot thread, README-gated
    └── outlines/           # one folder per outline, README-gated
```

**User:** looks good; proceed.

---

## Generate

Claude writes:

- `memex.config.json`
- `.memex/README.md` — folder map
- `.memex/AGENTS.md` — contract; "Required artifacts" table has rows for each type
- `.memex/index.md` — section headings
- `.memex/log.md` — seed entry
- `.memex/.open-questions/README.md`, `.memex/.rules/README.md`
- `.keep` files under each empty folder
- `CLAUDE.md` — from `templates/shared/claude.md.tmpl`, `{{ProjectName}}` = `my-novel`

---

## Post-scaffold

Claude prints the summary and the three next-step actions. The user starts by creating `.memex/wiki/characters/marek/README.md` and pasting the existing character bible content from `characters/marek.md` under it. The path-guard hook approves (slug folder, first write is README, frontmatter passes).

Within a week the project has 14 character pages, 6 places, 4 plot threads, and an index that cross-links them all. The research folder under `raw/` gets ingested by `/memex:ingest` into wiki summaries.

---

## What the user did NOT do

- Hand-author `memex.config.json`
- Hand-author `AGENTS.md`
- Figure out which frontmatter fields the hooks require
- Fight a `PreToolUse` block because `allowedTopLevel` didn't match `readmeRequired`

That's the win: the interview pre-validated every constraint, so the hooks never fire on day one.
