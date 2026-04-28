#!/usr/bin/env bash
# Toggle Memex on/off for the current project, used by the A/B harness.
#
# Renames `memex.config.json` to `.disabled` (or back). With the config
# missing, every Memex hook exits silently at the `load_config_from`
# branch — no SessionStart injection, no UserPromptSubmit retrieval, no
# Stop-hook context. The .memex/ directory and your wiki are untouched.
set -e

cfg=memex.config.json
off=memex.config.json.disabled

if [ -f "$cfg" ]; then
  mv "$cfg" "$off"
  echo "Memex DISABLED for this project. Restart Claude Code to apply."
elif [ -f "$off" ]; then
  mv "$off" "$cfg"
  echo "Memex ENABLED for this project. Restart Claude Code to apply."
else
  echo "No memex.config.json found in $(pwd) — is this a memex-enabled project?" >&2
  exit 1
fi
