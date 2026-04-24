---
title: Runbook rules
slug: runbook-rules
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Runbook rules

Runbooks exist so a tired on-call engineer at 3am can recover from an outage without paging a teammate. They are not aspirational — they describe what an operator actually does, step by step.

## 1. Who needs a runbook

Every system that can page someone. If a system has any of the following, it needs `runbooks/<slug>/README.md`:

- A PagerDuty / Opsgenie / equivalent alert wired up
- A critical user-facing dependency (auth, payments, database, core API)
- A scheduled job whose failure would be user-visible
- A third-party integration whose outage would degrade the product

If a system has no runbook, either (a) write one, or (b) remove the alert.

## 2. Location and frontmatter

**Location:** `runbooks/<slug>/README.md` — one folder per runbook; use same slug as the target system when there's a 1:1 mapping (e.g. `runbooks/auth/` for `platform/systems/auth/`).

**Frontmatter:**

```yaml
---
title: "Runbook: <system or alert name>"
slug: runbook-<kebab-slug>
type: runbook
status: draft|active|deprecated
owner: <team or individual responsible>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---
```

## 3. Required structure

```markdown
# Runbook: <name>

## Trigger
What alerts, pages, or symptoms send someone here?

- Alert name / paging rule: <name>
- Source: <PagerDuty / Grafana / Sentry / CloudWatch / ...>
- Example message: `<the literal string the on-call will see>`

## Symptom
What will the on-call observe from the outside?

- User-visible: <errors, slow responses, missing data>
- Dashboards to check: <links>
- Example log signature: `<grep-able string>`

## Diagnosis
Ordered, mechanical. Each step: observation \u2192 conclusion \u2192 next step.

1. Check <dashboard/log>. If you see X, jump to \u00a7 Remediation A. If you see Y, jump to \u00a7 Remediation B.
2. ...

Every branch must terminate in a remediation or an escalation. No dead ends.

## Remediation
For each diagnostic outcome: the exact command, config change, or rollback to apply.

### Remediation A — <named cause>
```
<literal commands, with placeholders marked <like-this>>
```
- Expected recovery time: <e.g. ~2 minutes>
- How to verify it worked: <what to check>

### Remediation B — ...

## Escalation
When to escalate, and to whom. Include out-of-hours path.

- Escalate if: <symptoms / duration / confidence threshold>
- Primary escalation: <person or team>
- Secondary escalation: <person or team>
- Vendor contact (if relevant): <support URL / email / phone>

## Validation
Once mitigated, how do you confirm the system is actually healthy?

- Metrics to watch: <list>
- Synthetic check to run: <command>
- Time to wait before declaring resolved: <duration>

## Related
- Owning system: [`platform/systems/<slug>/README.md`](../platform/systems/<slug>/README.md)
- Prior incidents: [`.incidents/DDMMYYYY-HHMM/`](../.incidents/...)
- Dependencies: <other runbooks this one might hand off to>
```

## 4. Keep it operator-grade

- **Commands must be literal.** Placeholders like `<region>` are fine; vague instructions like "use the admin panel to restart the service" are not.
- **No "see documentation elsewhere".** If the fix requires reading three other docs, inline the relevant pieces.
- **Test it.** At least once a quarter, an on-call runs the runbook against staging or in a drill. If it's out of date, update it.

## 5. Lifecycle

- **draft** — written, not yet validated by a real on-call event or drill.
- **active** — validated. Owned. Reviewed at least quarterly.
- **deprecated** — the system is gone or the runbook is superseded. Keep the file; explain why at the top.

When a runbook is used in anger, link it from the matching postmortem under `.incidents/`. If the runbook was wrong or incomplete, the postmortem's action items must include fixing it.
