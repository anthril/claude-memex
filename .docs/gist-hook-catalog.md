# A Hook Catalog for Enforcing Doc Discipline in Claude Code

A reference for building or reviewing a hook-based documentation enforcement layer. Every hook here is production-tested, small enough to audit in one sitting, and written to fail safe — when in doubt, allow the tool call rather than block it.

This catalog is organised by event. Within each event, the entries go from cheapest (path validation) to most intrusive (context injection). Read top-to-bottom to understand the surface; adopt selectively.

## Preliminaries

Every hook script in this catalog follows the same shape:

```python
#!/usr/bin/env python3
"""<hook-name>.py — <EventName> hook

What it enforces, and the rule file that documents why.
"""
import json, os, re, sys

def block(msg: str) -> None:
    sys.stderr.write(f"[<hook-name>] BLOCKED: {msg}\n")
    sys.exit(2)

def warn(msg: str) -> None:
    sys.stderr.write(f"[<hook-name>] WARNING: {msg}\n")

def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # ... logic ...
    sys.exit(0)

if __name__ == "__main__":
    main()
```

Three rules across the whole catalog:

1. **Exit 0 on any parse error.** A hook that crashes is a hook that blocks legitimate work. Always degrade to allow.
2. **Exit 2 for blocks, exit 0 for warnings.** Warnings go to stderr with a `WARNING:` prefix; Claude sees them but the tool call proceeds.
3. **Every error message names the rule.** `See .scribe/.rules/documentation-rules.md §3.` Good error messages are what make the system self-teaching.

## PreToolUse — gates

PreToolUse hooks run before a tool executes. Exit 2 prevents execution; stderr reaches Claude. This is where 90% of enforcement value sits.

### 1. `path-guard` — block bad paths before they exist

Matcher: `Write|Edit`. Purpose: enforce kebab-case, dated-folder format, and the top-level folder allowlist for your wiki tree.

Core checks:

- Top-level folder must be in an allowlist (e.g. `entities/`, `platform/`, `.audits/`, `.open-questions/`, and maybe eight others).
- Folder segments must match `^[a-z0-9]+(-[a-z0-9]+)*$`. No uppercase, no underscores, no spaces.
- Dated folders under `.audits/` and `.research/` must match `DDMMYYYY-HHMM` with no colons (colons are NTFS-invalid; don't let them into a cross-platform repo).
- Filenames must match the same kebab pattern, optionally with a two-digit ordering prefix (`01-data-model.md`).

Why this matters: the single biggest way doc discipline erodes is people creating `docs/`, `notes/`, `WIP/`, or `TODO.md` in random locations. Path-guard kills that at tool-call time. Once in place, nobody invents a new folder structure.

Pseudocode sketch:

```python
ALLOWED_TOP_LEVEL = {"README.md", "AGENTS.md", ".audits", ".research",
                     ".open-questions", ".rules", "entities", "platform", ...}
DATED_FOLDER_RE = re.compile(r"^\d{8}-\d{4}$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

def main():
    payload = json.load(sys.stdin)
    file_path = payload["tool_input"]["file_path"]
    norm = file_path.replace("\\", "/")
    if "/.wiki/" not in norm:
        sys.exit(0)
    rel = norm.split("/.wiki/", 1)[1]
    parts = rel.split("/")
    if parts[0] not in ALLOWED_TOP_LEVEL:
        block(f"'{parts[0]}' is not a permitted top-level folder.")
    for seg in parts:
        if ":" in seg:
            block(f"Colon in '{seg}' — invalid on Windows NTFS.")
        if " " in seg:
            block(f"Space in '{seg}'. Use kebab-case.")
    if parts[0] in (".audits", ".research") and len(parts) >= 2:
        if not DATED_FOLDER_RE.match(parts[1]):
            block(f"Dated folder '{parts[1]}' must match DDMMYYYY-HHMM.")
    # ... more checks ...
```

### 2. `readme-required` — no orphan subfolders

Matcher: `Write`. Purpose: if a new subfolder is being created under a tracked tree, the first file written must be its `README.md`.

The enforced trees are configurable — typically `platform/features/`, `platform/systems/`, `entities/`, `workers/`. Writing any other file into a new slug folder before the README exists is blocked.

This prevents the failure mode where someone creates `platform/features/billing/schema.md` and never gets around to writing the `README.md`. Three months later the folder is a pile of fragments with no entry point.

Logic:

- Is this a new file under a tracked tree? (Folder matches a pattern, parent doesn't yet have `README.md`.)
- Is the current write *itself* the `README.md`? → allow.
- Otherwise → block, tell Claude to write the README first.

### 3. `frontmatter-precheck` — don't let bad edits land

Matcher: `Edit` on paths matching `.wiki/**/README.md`. Purpose: when editing an existing README, verify the frontmatter is still intact before the edit lands. Complements the PostToolUse check; catches cases where an edit strips the frontmatter.

This one is mostly belt-and-braces. The PostToolUse version is the real line of defence.

### 4. `doc-required` — code without docs gets warned then blocked

Matcher: `Write|Edit`. Purpose: for each pattern declared in a `codeToDocMapping` config — code path → required doc path — verify the doc exists before the code gets written. Warn on first offence per session, block on second.

Example mapping:

```json
{
  "codeToDocMapping": [
    {
      "codePattern": "src/app/(console)/console/(dashboard)/*/",
      "requiresDoc": "platform/features/{1}/README.md",
      "severity": "warn-then-block"
    }
  ]
}
```

State-tracking is per-session under `.state/doc-misses.json`. First write to a missing-doc feature → warning, counter incremented. Second write → block.

This is the most valuable hook in the catalog for engineering projects. It makes "write the feature doc before the code" a default rather than a hope.

### 5. `ingest-doc-link` — nothing enters the system undocumented

Matcher: `Write`. Purpose: for patterns marked `severity: block` (typically database migrations, sometimes CLI scripts or Cloudflare workers), require a doc link either via:

- A header comment in the artifact (`-- Doc: .wiki/platform/features/billing/01-data-model.md`), or
- The artifact's slug/filename appearing in some markdown file under `.wiki/`.

Migration files without either get blocked. The first time Claude hits this, the error message includes both options verbatim — this is one of those hooks that *teaches* Claude the rule in one session.

Skeleton:

```python
def scan_wiki_for_slug(wiki_root, slug, filename):
    for root, _, files in os.walk(wiki_root):
        for f in files:
            if not f.endswith(".md"):
                continue
            with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                content = fh.read()
            if slug in content or filename in content:
                return True
    return False

# accept if header comment is present
if re.search(r"--\s*Doc:\s*\.wiki/[^\s\n]+", content):
    sys.exit(0)
# accept if slug is referenced anywhere in wiki
if scan_wiki_for_slug(wiki_root, slug, filename):
    sys.exit(0)
block(f"New migration {filename} has no linked doc. ...")
```

## PostToolUse — validators

PostToolUse runs after the tool completes. Exit 2 here surfaces as feedback to Claude; the tool call already succeeded but Claude is told to fix the follow-on issue.

### 6. `frontmatter-check` — every README has valid frontmatter

Matcher: `Write|Edit`. Purpose: after writing or editing a wiki README, validate required frontmatter fields.

```python
REQUIRED = ("title", "slug", "type", "status", "owner", "created", "updated")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()
m = FRONTMATTER_RE.match(content)
if not m:
    block(f"{file_path} is missing YAML frontmatter. Required: {REQUIRED}.")
body = m.group(1)
missing = [field for field in REQUIRED
           if not re.search(rf"^{field}\s*:\s*\S", body, re.MULTILINE)]
if missing:
    block(f"Frontmatter missing: {', '.join(missing)}.")
```

Optional stricter check: enforce that the `updated:` field was actually bumped. Compare the file on disk before and after (hash the previous content, store in session state, compare).

### 7. `index-update` — non-blocking nudge

Matcher: `Write`. Purpose: when a new wiki page is created, emit an `additionalContext` suggestion for the `index.md` line to add.

This doesn't block. It just tells Claude: "You created `entities/invoice/README.md` — add `- [Invoice](entities/invoice/README.md) — Core invoice entity.` to the index under `## Entities`."

Why non-blocking: index entries are a convention, not a correctness property. If Claude drops one, the next `wiki-lint` pass picks it up.

## SessionStart — context injection

### 8. `session-start-context` — boot with project memory

No matcher. Purpose: read the wiki's index head + last N log entries, emit them as `additionalContext`. Claude starts every session with awareness of what's in the wiki and what's changed recently.

```python
def main():
    payload = json.load(sys.stdin)
    wiki_root = find_wiki_root()  # walks up from CLAUDE_PROJECT_DIR
    index_head = read_head(os.path.join(wiki_root, "index.md"), lines=60)
    log_tail = read_tail(os.path.join(wiki_root, "log.md"), lines=15)
    context = f"## Wiki index (top)\n\n{index_head}\n\n## Recent activity\n\n{log_tail}"
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context
    }}))
```

This is the single biggest quality-of-life improvement in a mature wiki. Claude stops asking "which feature is this?" at the start of every session because it already knows.

## UserPromptSubmit — intent-aware context

### 9. `user-prompt-context` — grep-based RAG

No matcher. Purpose: when the user submits a prompt, extract keywords, search the wiki, surface the top few relevant pages.

Naive but effective:

1. Tokenise the prompt; drop stopwords.
2. `grep -l -r` for each remaining keyword across `.wiki/`.
3. Rank pages by number of hits; take top 3.
4. Return their paths + one-line frontmatter summary as `additionalContext`.

Swap to a proper search tool once the wiki passes ~200 pages — `qmd` gives you BM25 + vectors on-device, for example. Up to that point, grep is fine.

## Stop — reactive checks

The Stop event fires when Claude finishes responding to a user turn. It's the natural place to do "did we leave the system in a good state?" checks.

### 10. `stop-log-append` — auto-maintained ledger

No matcher. Purpose: append a log entry for the session or turn. Uses the tool-call log and any files touched to summarise.

```
## [2026-04-23] feature | invoice-cancellation — initial scaffold + data model
- Created platform/features/invoice-cancellation/README.md
- Created platform/features/invoice-cancellation/00-development-plan.md
- Added migration 20260423_add_cancellation_to_invoice.sql
- Linked open question: refund-policy.md
```

The prefix format matters: `## [YYYY-MM-DD] event | subject` is parseable with `grep "^## \[" log.md | tail -10`. You can query your own history from the terminal without a database.

### 11. `stop-stale-check` — catch drift between code and docs

No matcher. Purpose: for each wiki page, check whether its referenced code was touched this session AND the page's `updated:` frontmatter was NOT bumped. If so, list it.

The "referenced code" logic:

- Parse each wiki README for links into the codebase (`src/...`, `supabase/...`, etc.).
- Cross-reference against the session's tool-call log of files written/edited.
- If a page's referenced files were touched but the page itself wasn't, flag it.

Emit as stderr warning or `additionalContext`. Claude can pick up the stale pages in a follow-up turn. Much cheaper than a monthly audit.

### 12. `stop-open-questions-check` — catch inline TBDs

No matcher. Purpose: grep Claude's wiki writes for `TODO`, `TBD`, `XXX`, `????`. If found in a wiki doc, propose promoting to `.open-questions/`.

One of the hardest doc conventions to enforce is "no unresolved questions inline." This hook handles it: you don't have to read every doc Claude writes; the runtime checks for the markers and prompts for promotion.

## PreCompact — preserve synthesis

### 13. `precompact-snapshot` — save before the context window collapses

No matcher. Purpose: before Claude compacts conversation history, write a session-summary file to `.wiki/.state/sessions/<session-id>.md`.

This is opt-in by default (sessions-snapshot is gitignored unless you enable commit). The reason to have it: a compacted conversation loses the intermediate reasoning that produced the final wiki edits. If you're publishing research on LLM behaviour (or debugging agent failures), you want those intermediates preserved.

## SessionEnd — close the loop

### 14. `session-end-log` — final ledger entry

No matcher. Purpose: append a session-close entry with duration, tool-call counts, and pages touched.

Useful both as an audit trail and as a feedback loop — if you notice sessions ending with 80 tool calls and zero doc edits, the enforcement stack isn't doing its job.

## Wiring it all together

The hooks above go in `hooks.json` (or inline in `plugin.json`). A condensed version:

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks":[{"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-start-context.py","timeout":5000}]}
    ],
    "UserPromptSubmit": [
      {"hooks":[{"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/user-prompt-context.py","timeout":5000}]}
    ],
    "PreToolUse": [
      {"matcher":"Write|Edit","hooks":[
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/path-guard.py","timeout":5000},
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/doc-required.py","timeout":5000}
      ]},
      {"matcher":"Write","hooks":[
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/readme-required.py","timeout":5000},
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/ingest-doc-link.py","timeout":5000}
      ]}
    ],
    "PostToolUse": [
      {"matcher":"Write|Edit","hooks":[
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/frontmatter-check.py","timeout":5000},
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/index-update.py","timeout":5000}
      ]}
    ],
    "Stop": [
      {"hooks":[
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-log-append.py","timeout":10000},
        {"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-stale-check.py","timeout":10000}
      ]}
    ],
    "PreCompact": [
      {"hooks":[{"type":"command","command":"python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/precompact-snapshot.py","timeout":10000}]}
    ]
  }
}
```

## Adoption order

If you're adding this to an existing project, don't ship all fourteen hooks at once. A stepped adoption:

1. **Path-guard + readme-required + frontmatter-check.** One afternoon of work. Catches the vast majority of structural violations. Ship this first.
2. **Doc-required + ingest-doc-link.** One more session. Adds the code-to-doc linkage; this is where enforcement stops being cosmetic and starts shaping behaviour.
3. **Session-start-context + user-prompt-context.** Week two. These are quality-of-life; they only pay off once the wiki has enough content to surface useful results.
4. **Stop-log-append + stop-stale-check.** The "wiki stays in sync" layer. Adds real work per session but catches drift early.
5. **Precompact-snapshot + session-end-log.** Last. Optional unless you're doing research on agent behaviour.

Each step is shippable on its own. You can stop after step 1 and still be better off than a typical project.

## A note on failure modes

Things that go wrong when you deploy a hook stack like this:

- **False positives from overly strict rules.** Always fail safe: prefer warn over block for anything non-structural. When you do block, the error message must name the exact fix.
- **Hook timeouts.** Default is 60s, practical ceiling is 10s. If a hook is slow, cache results or move work off the hot path.
- **Session-scoped state.** Counters (like `doc-required`'s warn-then-block) need a state file scoped to the session. Use `${CLAUDE_SESSION_ID}` in the filename so parallel sessions don't collide.
- **Cross-platform paths.** Normalise with `file_path.replace("\\", "/")` once, then stay in forward-slash land. Windows paths in regex are a known source of bugs.
- **"Bypassing a hook."** Forbid it in `AGENTS.md`. If a hook is wrong, fix the hook or file an open question. Never disable mid-session.

## Takeaway

Fourteen hooks, maybe 1500 lines of Python in aggregate, replace what most teams are currently trying (and failing) to enforce through style guides and code review. The trick isn't individual hook cleverness. It's the composition: gates at tool call, validators after tool call, context injection at session boundaries, reactive checks at session stop.

Build the stack once. Run it against every project. Stop pretending documentation discipline can be a convention.

---

*The hook patterns above are derived from a production enforcement layer at Lumioh (operations documentation for an agentic SaaS platform) and the LLM-wiki pattern for compounding knowledge bases. A reference plugin implementation is in progress; this catalog is written to stand on its own regardless of which plugin or scaffold you use.*
