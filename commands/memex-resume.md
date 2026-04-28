---
description: Reload the next-session brief on demand (replaces the old auto-fetch on session start)
argument-hint: "(no arguments)"
allowed-tools: Read, Glob
---

# /memex:resume

Re-read the project's "what's next" brief and re-orient. This command exists so the brief only lands in context when you actually want it — auto-injection on every session start was burning tokens for sessions that didn't need the pickup.

## Usage

```
/memex:resume
```

## Behaviour

Look for the brief in this order, stop at the first hit, and print its contents back as a quoted block followed by a 3–5-sentence summary of the top priorities:

1. **`NEXT-SESSION.md`** at the project root (Aurora's convention — capitalised, top-level)
2. **`<root>/next-session.md`** (Lumioh's convention — lowercase, inside the wiki root from `memex.config.json#/root`, e.g. `.memex/next-session.md`)
3. **`<root>/NEXT-SESSION.md`** (alternative capitalisation inside the wiki root)
4. **`<root>/sessions/NEXT-SESSION.md`** (if the wiki uses a `sessions/` folder)

If none exist:

```
No next-session brief found. Looked at:
  - NEXT-SESSION.md
  - <root>/next-session.md
  - <root>/NEXT-SESSION.md
  - <root>/sessions/NEXT-SESSION.md

To create one, write a brief to one of those paths at session-end. The
session-end protocol in `<root>/AGENTS.md` typically covers regeneration.
```

After printing the brief, summarise:

- Top 3 priorities (numbered)
- Anything blocked / awaiting external action
- A single suggested first move

Then ask which priority to start, unless the user already named one in the same turn.

## Steps for the agent

1. Resolve the project root by walking up from cwd looking for `memex.config.json` or a wiki root directory (`.memex/` is the default; respect the `root` key in `memex.config.json` if present).
2. Use `Glob` to check the candidate paths above.
3. Read the first hit with `Read`.
4. Quote the contents (or first ~50 lines if very long) so the user sees what you're working from.
5. Synthesise the 3–5-sentence summary.

## When NOT to use this

- During a fresh session where you already have full context — the brief duplicates state that's already loaded.
- For multi-step task tracking inside a session — that's what TodoWrite is for.
- For chronological history — read `<root>/log.md` tail instead.
