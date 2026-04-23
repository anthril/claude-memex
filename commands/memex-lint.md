---
description: Health-check the Memex wiki
argument-hint: "[scope]"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
---

# /memex:lint

Health-check the wiki: orphans, contradictions, stale claims, missing cross-references, overdue open questions, dangling links, code-to-doc mapping gaps.

## Usage

```
/memex:lint                     # lint the whole wiki
/memex:lint platform/features   # lint only a subfolder
```

## Behaviour

Invokes the `wiki-lint` skill (`skills/wiki-lint/SKILL.md`).

For large wikis (> 50 `.md` files under the ops root), **delegate to the `memex-linter` subagent** for isolation so the main session doesn't inherit the churn.

## Output

- A severity-grouped table of findings (`issue | warn | info`)
- A link-graph summary
- An open-questions summary
- Suggested next actions
- (If scope = whole wiki) an offer to save the report to `<ops-root>/.audits/<DDMMYYYY-HHMM>/lint-report.md`

## Auto-fix

The skill offers to auto-fix only the trivially mechanical items:

- Missing `index.md` entries → append
- Orphan pages → add "See also" link from the best parent
- Dangling links → create stub OR remove

Contradictions and stale-claim warnings are never auto-fixed — they need human judgement.
