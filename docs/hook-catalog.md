# Hook catalog

Every hook shipped by the Memex plugin, with the event that fires it, what it enforces, and how it fails. The plugin-level wiring lives in [`../hooks/hooks.json`](../hooks/hooks.json).

---

## PreToolUse — blocking gates

These run before the tool call. `exit 2` blocks; stderr is surfaced to Claude's next turn.

| Hook | Matcher | What it does | On violation |
|---|---|---|---|
| [path-guard.py](../hooks/scripts/path-guard.py) | `Write\|Edit` | Enforces `allowedTopLevel`, `datedFolders` format, and kebab-case naming on all writes under the ops root | `exit 2` with the exact rule violated |
| [doc-required.py](../hooks/scripts/doc-required.py) | `Write\|Edit` | For each `codeToDocMapping` entry, requires the linked doc to exist before the code lands. Warn-then-block via `.memex/.state/`. | Warn on first offence; block on second |
| [readme-required.py](../hooks/scripts/readme-required.py) | `Write` | In a `readmeRequired` slug folder, the first file written MUST be `README.md` | `exit 2` naming the slug folder |
| [ingest-doc-link.py](../hooks/scripts/ingest-doc-link.py) | `Write` | Migration-like artifacts (patterns with `severity: block`) must either reference a doc header-comment or be referenced from a wiki page | `exit 2` suggesting both remedy forms |
| [frontmatter-precheck.py](../hooks/scripts/frontmatter-precheck.py) | `Edit` | Warn if an existing wiki page already has broken frontmatter before we edit it | Warn only (not blocking) |

## PostToolUse — validators

Run after the tool call. `exit 2` here blocks the NEXT tool call and surfaces stderr.

| Hook | Matcher | What it does | On violation |
|---|---|---|---|
| [frontmatter-check.py](../hooks/scripts/frontmatter-check.py) | `Write\|Edit` | Validates frontmatter required fields + enum values on any file matching `frontmatter.appliesTo` | `exit 2` listing missing/invalid fields |
| [index-update.py](../hooks/scripts/index-update.py) | `Write\|Edit` | Non-blocking reminder if a new page isn't referenced from `index.md` | `additionalContext` only |

## SessionStart

| Hook | What it does |
|---|---|
| [session-start-context.py](../hooks/scripts/session-start-context.py) | Injects `index.md` head + last N `log.md` entries into Claude's context. N from `hookEvents.sessionStart.injectRecentLog`. |
| [update-check.py](../hooks/scripts/update-check.py) | Opt-in (`hookEvents.sessionStart.updateCheck: true`) — polls GitHub for newer releases once every 24h. Cached at `.memex/.state/update-check.json`. Silent and off by default; fail-closed on any network error. |

## UserPromptSubmit

| Hook | What it does |
|---|---|
| [user-prompt-context.py](../hooks/scripts/user-prompt-context.py) | Keyword-based retrieval over the wiki; surfaces top-3 matching pages as `additionalContext`. Grep by default; `qmd` if configured and on PATH. |

## Stop

All three run on conversation stop. Non-blocking — they emit `additionalContext` or write files but never `exit 2`.

| Hook | What it does |
|---|---|
| [stop-log-append.py](../hooks/scripts/stop-log-append.py) | Appends a `log.md` entry using the `log.entryPrefix` template |
| [stop-stale-check.py](../hooks/scripts/stop-stale-check.py) | Flags wiki pages whose referenced code was touched but whose `updated:` was not bumped |
| [stop-open-questions-check.py](../hooks/scripts/stop-open-questions-check.py) | Detects inline TODO/TBD/XXX/FIXME markers in session-written wiki pages; prompts promotion |

## PreCompact

| Hook | What it does |
|---|---|
| [precompact-snapshot.py](../hooks/scripts/precompact-snapshot.py) | Writes a lightweight session snapshot to `.memex/.state/sessions/<id>.md` before the conversation compacts. Preserves synthesis that would otherwise be lost. |

## SessionEnd

| Hook | What it does |
|---|---|
| [session-end-log.py](../hooks/scripts/session-end-log.py) | Appends a final `log.md` entry with the session end reason |

---

## Hook output contracts

All hooks follow Anthropic's Claude Code hook I/O contract:

- **Input:** JSON on stdin. Includes `tool_name`, `tool_input`, `session_id`, `transcript_path`, `cwd`.
- **Output:** exit code + stderr (PreToolUse / PostToolUse blocking) OR JSON on stdout with `hookSpecificOutput.additionalContext` (for context injection).
- **Exit codes:** `0` allow; `2` block; other non-zero values are treated as hook errors and the tool call is allowed to proceed.

See Anthropic's [hooks reference](https://code.claude.com/docs/en/hooks) for the full protocol.

## Configuration surface

All behaviour is driven by `memex.config.json`:

- `root` — where the wiki lives
- `allowedTopLevel` — path-guard's whitelist
- `datedFolders.paths` / `datedFolders.format` — dated-folder rules
- `readmeRequired` — slug patterns requiring README first
- `frontmatter.appliesTo` / `frontmatter.required` / `frontmatter.enum` — frontmatter rules
- `naming.asciiOnly` — if `true`, restrict kebab slugs to ASCII; defaults to `false` (Unicode-friendly)
- `codeToDocMapping` — feeds `doc-required.py` and `ingest-doc-link.py`
- `hookEvents.*` — per-event tuning (N for log injection, `updateCheck`, stop-hook toggles, etc.)
- `search.engine` — `grep` (default) or `qmd`
- `updateCheckUrl` — optional mirror URL for the update-check hook (corporate environments)

Every hook reads this file first. If the file is missing, the hook exits silently — so the plugin is inert in projects that haven't been init'd.
