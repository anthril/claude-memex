# Credits & prior art

Memex is a synthesis of several existing ideas. This file names each input and what it contributed. Nothing here is Memex's original invention except the specific packaging: a Claude Code plugin + seedable template + hook-enforced schema reading a portable config.

---

## Andrej Karpathy — `llm-wiki.md` (April 2026)

**The conceptual origin.** Karpathy's gist describes the LLM-maintained personal wiki pattern:

- Three layers: raw sources (immutable), the wiki (LLM-authored markdown), and the schema (a CLAUDE.md / AGENTS.md describing the conventions)
- Three operations: **ingest** new sources, **query** the wiki, **lint** for contradictions, orphans, stale claims
- Two special files: `index.md` (content-oriented catalogue) and `log.md` (chronological ledger with parseable prefixes)
- The core observation: **the wiki is a persistent, compounding artifact**, not a set of chunks retrieved on demand. The LLM writes and maintains it; the human curates sources and asks questions.

Links:

- Original gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- All of Karpathy's gists: https://gist.github.com/karpathy
- Karpathy on GitHub: https://github.com/karpathy

Every concept Memex implements — raw/wiki/schema split, ingest/query/lint, index + log with parseable prefix, Obsidian-as-IDE, compounding synthesis — originates in Karpathy's gist.

What Memex adds on top: a portable schema file so the pattern works across domains, and hook-enforced discipline so the wiki stays healthy without human babysitting.

---

## Vannevar Bush — "As We May Think" (1945)

The name **Memex** comes from Bush's 1945 essay in *The Atlantic* describing a personal knowledge device with associative trails between documents — private, actively curated, with the connections between documents as valuable as the documents themselves. Karpathy's gist closes with this same attribution. Bush's essay is widely cited as prefiguring hypertext, the web, and the personal knowledge base as a distinct artifact from public-facing publication.

Read it: https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/

---

## Anthropic — `claude-md-management` plugin

Official Anthropic plugin that audits `CLAUDE.md` and rolls session learnings into it. Confirms Anthropic's own position that CLAUDE.md should be Claude-maintained, not hand-edited. Memex is **complementary**: the management plugin handles the one-file memory problem; Memex handles the broader multi-page knowledge tree. Projects are encouraged to use both.

Repo: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management

---

## Anthropic — Claude Code hooks

The enforcement layer this plugin is built on. Memex uses `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`, `PreCompact`, and `SessionEnd` events. The `exit 2` blocking convention + stderr-as-feedback-to-Claude pattern is Anthropic's design; Memex just applies it systematically to doc discipline.

Hooks reference: https://code.claude.com/docs/en/hooks
Plugins reference: https://code.claude.com/docs/en/plugins-reference

---

## `qmd` by Tobias Lütke — local markdown search

Optional integration for the research-wiki profile at larger scales. Memex's `user-prompt-context` hook uses plain grep by default; if `qmd` is installed and enabled in `memex.config.json`, it shells out to `qmd` for BM25 + vector search over the wiki. This is lifted directly from a suggestion in Karpathy's gist.

Repo: https://github.com/tobi/qmd

---

## Others

- **Obsidian** — the markdown IDE the wiki is designed to be readable in. Dataview-compatible frontmatter is preserved throughout.
- **Obsidian Web Clipper** — noted in Karpathy's gist as the standard tool for getting web articles into `raw/` for the research-wiki profile.
- **Marp** — markdown slide format, suggested in the gist for one-off query outputs that file back into the wiki.

---

## Licence

Memex is MIT-licensed. Karpathy's gist is cited and linked; no verbatim copy is redistributed. If Karpathy prefers a different attribution form, open an issue and we'll adjust.
