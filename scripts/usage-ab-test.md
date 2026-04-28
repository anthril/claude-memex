# A/B test: is Memex actually burning your tokens?

If you suspect Memex hooks are inflating your Claude Code token usage,
this 5-minute protocol gives you a real number instead of a hunch.

## Protocol

### Baseline — Memex enabled

1. Open a memex-enabled project (one with a `.memex/` folder) in Claude Code.
2. Start `claude --debug`.
3. Run **5 typical interactions** (whatever you'd normally do — read a file,
   ask a question, edit something, etc.).
4. Note the token count from the status bar after each interaction.
5. Record the **total tokens consumed** for the session.

### Comparison — Memex disabled

1. In the same project, rename the **config file** so every hook silently
   exits:
   ```bash
   # bash / git-bash
   mv memex.config.json memex.config.json.disabled
   # PowerShell
   Move-Item memex.config.json memex.config.json.disabled
   ```
   `find_project_root()` will still locate the project via the leftover
   `.memex/` directory, but `load_config_from()` returns `None` because
   the config file is gone — and every Memex hook exits at that branch
   before injecting any context. Renaming `.memex/` alone is **not enough**:
   the hooks fall back to discovering the project via `memex.config.json`,
   so both the directory and the config drive the discovery.
2. Restart Claude Code (so `SessionStart` re-fires without Memex context).
3. Run the **same 5 interactions** as before — same files, same questions,
   same edits. Use a fresh context to avoid cache effects.
4. Record total tokens again.

### Restore

```bash
# bash / git-bash
mv memex.config.json.disabled memex.config.json
# PowerShell
Move-Item memex.config.json.disabled memex.config.json
```

### Toggle helper (optional)

If you'll be flipping back and forth, drop this in `scripts/memex-toggle.sh`:

```bash
#!/usr/bin/env bash
set -e
cfg=memex.config.json
off=memex.config.json.disabled
if [ -f "$cfg" ]; then
  mv "$cfg" "$off" && echo "Memex DISABLED for this project."
elif [ -f "$off" ]; then
  mv "$off" "$cfg" && echo "Memex ENABLED for this project."
else
  echo "No memex.config.json found — is this a memex-enabled project?" >&2
  exit 1
fi
```

(PowerShell equivalent uses `Move-Item` with the same logic.)

### (Optional) Cross-project check

To isolate Memex from your other plugins, repeat the baseline step in a
project that has **never** had Memex installed (no `.memex/` folder).
That session's overhead is purely from your global plugins + CLAUDE.md +
the Claude Code system prompt — not Memex.

## Interpreting the result

| Result                                          | Conclusion                                     |
|-------------------------------------------------|------------------------------------------------|
| Disabled-Memex session ≥ 90 % of baseline cost  | Memex isn't the bottleneck. Look at: total plugin count (each adds skill descriptions to the system prompt), long sessions (transcript size grows linearly), or the Anthropic 5-min cache window. |
| Disabled-Memex session 60-90 % of baseline cost | Memex is contributing measurable overhead. The conservative fixes in this repo (single Stop-hook orchestrator, cached `index.md` parse) trim CPU but not tokens — for token cuts, see the next section. |
| Disabled-Memex session < 60 % of baseline cost  | Memex is a major contributor. Apply the per-project tunings below. |

## Tuning Memex for lower token usage

These knobs already exist — you just need to set them in your project's
`memex.config.json`:

```jsonc
{
  "search": {
    "maxContextPages": 1     // default 3 — cuts UserPromptSubmit cost ~3×
  },
  "hookEvents": {
    "sessionStart": {
      "injectIndex": false,     // default true — skip the 3 KB index head
      "injectRecentLog": 0      // default 5 — skip recent log entries
    },
    "stop": {
      "appendLog": false,       // default true — skip log append (rarely costly)
      "staleCheck": false       // default true — skip stale-doc detection
    }
  }
}
```

For the most aggressive reduction, set `maxContextPages: 0` to disable
per-prompt retrieval entirely — Claude won't get auto-suggested wiki pages,
but you can still query the wiki manually with `/memex:query`.
