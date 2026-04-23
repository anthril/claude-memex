# Beyond CLAUDE.md: Claude-Maintained Project Memory

Most Claude Code projects have a `CLAUDE.md`. Fewer have a documentation system that stays current. The gap between those two things is where almost all the rot happens — and where the most valuable agent automation is sitting unused.

This post is about closing that gap. The pattern is simple enough to sketch in an afternoon and strong enough to replace most of what an engineering team's wiki does today.

## The three states of project documentation

Every project's docs are in one of three states.

**State 1 — No docs.** `CLAUDE.md` is a few lines; everything else lives in chat history, commit messages, and someone's head. This is where most projects start. Claude does its best to rediscover the codebase on every session. It's cheap to set up and expensive to operate.

**State 2 — Human-maintained wiki.** Someone wrote a Notion page, a Confluence tree, a `/docs` folder. The docs were great at launch. Three sprints later nobody's sure which parts are current. The wiki becomes a liability: consulted, believed, and wrong. Humans abandon wikis because the maintenance burden grows faster than the value.

**State 3 — Claude-maintained wiki.** The docs are a structured tree of markdown. An LLM writes them, updates them, cross-references them, and flags contradictions. The human's job is to curate sources, ask questions, and review. The LLM's job is everything else: summarising, filing, maintaining links, bumping changelogs, noticing when a new source contradicts the old synthesis.

The trick to State 3 is that it doesn't actually need clever AI. It needs two things:

1. **A tight contract about where documents live** — tight enough that the LLM never has to guess.
2. **Enforcement at tool-call time** — blocking the moment something violates the contract, not catching it in a PR review three days later.

That second piece is where Claude Code hooks change everything.

## Why CLAUDE.md alone isn't enough

`CLAUDE.md` is project memory. It's necessary but not sufficient. It's one file, read at session start, covering things like build commands and architecture notes.

What it can't do:

- **Scale past a page.** A 2000-line `CLAUDE.md` stops being read carefully.
- **Branch by topic.** You can't have separate pages for each entity, each feature, each subsystem.
- **Accumulate.** Every edit to `CLAUDE.md` is a merge conflict waiting to happen. You can't compound knowledge there.
- **Cross-reference itself.** One file can't have a graph of internal links that lights up an Obsidian-style view of the project.

Anthropic ships an official `claude-md-management` plugin that audits `CLAUDE.md` and rolls session learnings into it. That's a good tool for the one-file problem. It doesn't replace the need for a broader, multi-page knowledge tree.

## The pattern

Call it whatever you like. The shape is:

```
your-project/
├── .claude/
│   ├── CLAUDE.md          # Short. Points at the wiki.
│   └── settings.json      # Hooks that enforce discipline.
├── .wiki/                 # Or .operations/, .scribe/, .docs/...
│   ├── AGENTS.md          # Binding contract for every agent.
│   ├── README.md          # Folder map.
│   ├── index.md           # Content-oriented catalogue.
│   ├── log.md             # Chronological ledger.
│   ├── .open-questions/   # Unresolved items, one file per topic.
│   ├── .rules/            # Ecosystem rules.
│   ├── entities/          # Or topics/, characters/, concepts/...
│   └── ...
└── [your code]
```

Three layers, borrowed from the LLM-wiki pattern:

**Raw sources** — the code itself, plus any external articles/papers/transcripts. Immutable; the LLM reads them, never modifies them.

**The wiki** — LLM-generated markdown. Summaries, entity pages, concept pages, analyses. The LLM owns this layer. The human reads it.

**The schema** — `AGENTS.md` + `CLAUDE.md` + a config file that tells every agent how the wiki is structured and what the rules are.

## Three operations and a log

Operationally, everything happens through three verbs plus a ledger:

**Ingest.** A new source arrives — an article, a meeting transcript, a chapter, a research paper. The LLM reads it, writes a summary page, updates every entity/concept page the source touches, updates the index, appends a log entry. One source can touch fifteen pages. The human watches.

**Query.** A question is asked. The LLM searches the index, reads relevant pages, synthesises a cited answer. Good answers get filed back into the wiki as new analysis pages. This is how your explorations compound instead of evaporating into chat history.

**Lint.** Periodically, an audit pass. Look for contradictions, stale claims newer sources have superseded, orphan pages with no inbound links, important concepts mentioned but lacking their own page, gaps that warrant a search.

Underneath it all, a chronological `log.md` that uses a parseable prefix format — `## [YYYY-MM-DD] event | subject`. The log becomes queryable with `grep "^## \[" log.md | tail -10`. Cheap, portable, versionable.

## Enforcement at tool-call time

Here's the part that makes the pattern actually work: **Claude Code hooks block violations before they happen.**

A hook is a shell command Claude Code runs in response to lifecycle events — before a tool call, after a tool call, when the user submits a prompt, when a session starts, when a session stops. If the hook exits with code 2, the tool call is blocked and the hook's stderr message is sent back to Claude as feedback.

This is the difference between a convention and a contract. Conventions are what you write in a `STYLE.md` and hope everyone follows. Contracts are what the runtime refuses to execute when violated.

A short list of hooks that do most of the work:

- **`path-guard` (PreToolUse Write/Edit).** Blocks writes outside the permitted folder tree. Blocks non-kebab-case filenames. Blocks colon-containing dated folders (which break NTFS). Blocks ad-hoc `docs/`, `notes/`, `WIP/` directories.
- **`readme-required` (PreToolUse Write).** If you're creating a new feature folder, the first file written must be `README.md`. No orphan subfolders.
- **`frontmatter-check` (PostToolUse Write/Edit).** After every README edit, parses the YAML frontmatter. Missing `title`, `slug`, `type`, `status`, `owner`, `created`, `updated`? Exit 2, explain what's missing.
- **`doc-required` (PreToolUse Write/Edit).** Writing a new feature route? If there's no matching feature doc, warn on first write, block on second. Session-scoped counter in local state.
- **`ingest-doc-link` (PreToolUse Write).** New database migration? Either its slug must be referenced from somewhere in the wiki, or it must carry a `-- Doc: .wiki/...` header comment. Undocumented schema changes don't ship.
- **`session-start-context` (SessionStart).** Reads the top of `index.md` and the last few `log.md` entries, emits them as `additionalContext`. Claude boots with project memory loaded.
- **`user-prompt-context` (UserPromptSubmit).** Extracts keywords from the prompt, greps the wiki, surfaces top-3 relevant page paths. The poor-man's RAG.
- **`stop-log-append` (Stop).** Appends a log entry summarising the session.
- **`stop-stale-check` (Stop).** For every wiki page whose referenced code was touched this session without a bumped `updated:` field — list them. The wiki stays in sync with the code because the runtime notices when it isn't.

Each hook is fifty to a hundred lines of Python or Node. Any one of them written in isolation is a toy. The set of them — wired into the session lifecycle — is a system.

## What this looks like in practice

A typical session:

1. You start Claude Code. `session-start-context` runs. Claude boots with the current `index.md` summary and the last five log entries. It knows, without you typing anything, what's recently changed and where things live.
2. You ask: "add an invoice-cancellation flow." `user-prompt-context` greps the wiki, surfaces `entities/invoice/README.md`, `platform/features/billing/README.md`, and `.open-questions/refund-policy.md`.
3. Claude proposes code. `doc-required` fires: there's no feature doc for `invoice-cancellation` yet. Warning emitted: "Create `.wiki/platform/features/invoice-cancellation/README.md` with full frontmatter before adding code. Next edit will be blocked."
4. You or Claude creates the feature README. `frontmatter-check` runs: missing `updated` field. Exit 2. Fixed in the next turn.
5. Code gets written. A migration is created. `ingest-doc-link` fires: the migration's slug isn't linked anywhere yet. Claude adds the `-- Doc: ...` header comment; the hook passes.
6. Work completes. `stop-log-append` writes `## [2026-04-23] feature | invoice-cancellation — initial scaffold` to `log.md`. `stop-stale-check` confirms every touched wiki page got bumped. Done.

At no point did you type "please update the docs." The system noticed every time it needed updating and refused to proceed until it was.

## Why now

Three things converged.

**The hook surface matured.** As of early 2026 Claude Code has ~18 hook events covering essentially the full session lifecycle. You can inject context at session start, validate at tool call, react at task completion, snapshot before compaction. A year ago this wasn't possible; six months ago it was fragile.

**Plugins shipped.** The plugin model (`.claude-plugin/plugin.json` + component directories) lets you version the hook logic in one place and apply it to many projects. The enforcement scripts don't need to be copy-pasted per repo.

**The bookkeeping cost is near zero.** Humans abandoned wikis because the maintenance burden grew faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch fifteen files in one pass. Vannevar Bush's 1945 Memex essay described exactly this kind of personal, curated, linked knowledge store — with associative trails between documents as valuable as the documents themselves. The part Bush couldn't solve was who does the maintenance. We finally have an answer.

## What to do about it

If you have a project that already suffers from State 1 or State 2 docs, the shortest path is:

1. Pick a single folder — `.wiki/`, `.operations/`, whatever — and commit to it being the only place docs live.
2. Write a one-page `AGENTS.md` that says where each kind of document goes.
3. Add three hooks to start: path-guard, readme-required, frontmatter-check. Keep them small. Let them block.
4. Run for a week. Every time the hooks fire on a false positive, fix the rule. Every time they block a real violation, note the near-miss.
5. Add ingest and query workflows later. Add session-lifecycle hooks later. Lint last.

The first three hooks plus a `.wiki/` tree plus a one-page contract is ninety percent of the value. Everything else is refinement.

The goal isn't to build the perfect wiki. It's to reach the state where the docs are current by default, not by effort — and then let that state compound.

---

*The pattern described here has a reference implementation in progress under the working name "Scribe," shipped as a Claude Code plugin plus a set of project templates. The hook logic generalises the enforcement pattern used in production at Lumioh. The wiki operations generalise the LLM-wiki pattern that's been circulating among people building long-running research notebooks. Neither half works alone. Together they work well enough to replace most of what a team's documentation system is currently failing to do.*
