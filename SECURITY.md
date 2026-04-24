# Security policy

## Supported versions

During alpha, only the latest release gets security updates. Once v1.0 ships, we'll maintain the most recent minor version line and publish an end-of-life notice for older versions at least 30 days before dropping them.

| Version | Supported |
|---|---|
| `0.1.x-alpha.*` | :white_check_mark: |
| anything older  | :x: |

## Threat model

`claude-memex` is a Claude Code plugin shipping Python hook scripts and markdown templates. It:

- Runs hook scripts with the same privileges as the user's Claude Code session
- Reads and writes files under the target project's `.memex/` directory
- Parses `memex.config.json` — a project-owned file
- Optionally (opt-in) makes one GitHub API request per 24 hours to check for updates
- Optionally (opt-in) shells out to `qmd` if the user configures it

It does NOT:

- Send any project content or telemetry to external services
- Execute code from wiki pages (markdown is treated as text)
- Run with elevated privileges
- Store credentials anywhere

## Reporting a vulnerability

**Please do not file public GitHub issues for security problems.**

Report via one of:

- GitHub Security Advisories — https://github.com/anthril/claude-memex/security/advisories/new (preferred)
- Email the maintainers at `security@anthril.dev` (drop us a line — PGP key available on request)

Include:

1. A description of the issue
2. Steps to reproduce (ideally a minimal `.memex/` tree or config that triggers it)
3. Expected vs. observed behaviour
4. The commit SHA or release tag you tested against

We aim to:

- Acknowledge within **3 working days**
- Provide an initial assessment within **7 working days**
- Ship a fix or mitigation within **30 days** for issues rated High or Critical

## Scope

In scope:

- The plugin's hook scripts under `hooks/scripts/`
- Ancillary scripts under `scripts/`
- The Python helper library `hooks/scripts/_lib/`
- The schemas + template tree shipped with the plugin

Out of scope (report to the relevant upstream instead):

- Claude Code itself — https://www.anthropic.com/security
- Anthropic's claude-md-management plugin — https://github.com/anthropics/claude-plugins-official
- `qmd` — https://github.com/tobi/qmd
- Project-owned wiki content (the plugin doesn't validate user-authored markdown for safety)

## Credit

Security researchers who report valid vulnerabilities will be credited in the release notes and `CREDITS.md` (unless they prefer anonymity).
