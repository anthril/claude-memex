---
title: Incident rules
slug: incident-rules
type: rule
status: active
owner: unassigned
created: 2026-04-24
updated: 2026-04-24
---

# Incident rules

Every production incident gets a blameless postmortem. The format is fixed; the tone is contractually blameless.

## 1. When to file

An incident is any event that caused:

- User-visible degraded service (errors, slowness, missing data, wrong data)
- Data loss or data corruption (even if recovered)
- Security incident (real or suspected breach, leaked credentials, unauthorised access)
- A near-miss that would have caused any of the above had it not been caught

Small enough to not matter? File a one-paragraph entry anyway. The cheapest thing in the world is a one-paragraph postmortem you wrote and forgot.

## 2. Location and timing

- **Location:** `.incidents/DDMMYYYY-HHMM/README.md` — timestamp is when the incident *started*, not when you're writing it up
- **Timing:** within the first session after recovery. Not "some day". Now.

## 3. Required frontmatter

```yaml
---
title: "Incident: <one-line summary>"
slug: incident-<kebab-slug>
type: incident
status: draft|active|deprecated
owner: <incident commander>
created: <YYYY-MM-DD of the incident>
updated: <YYYY-MM-DD>
---
```

## 4. Required sections

```markdown
# Incident: <one-line summary>

## Impact
- **User impact:** who was affected, for how long, how severely
- **Data impact:** any data lost, corrupted, or exposed
- **Systems:** which systems were affected (link to `platform/systems/<slug>/`)
- **Blast radius:** % of users, geographic scope, tier/plan scope

## Timeline
UTC timestamps. Every entry should be terse and factual.

- `HH:MM` — <what happened or was observed>
- `HH:MM` — <next event>
- ...

Include at minimum:
- **Start:** first user-visible symptom (even if no-one noticed yet)
- **Detection:** when paged / when humans knew
- **Mitigation:** when user impact stopped (even if system not fully fixed)
- **Resolution:** when fully back to green

## Root cause
One paragraph. What actually broke? Mechanical, not human.

Bad: "Bob forgot to add the index."
Good: "A new query introduced by ADR-0042 ran without an index because our migration process doesn't run EXPLAIN on new queries before merge."

## Contributing factors
Bullet list. Things that made this worse, slower to detect, or slower to resolve.

## What went well
Bullet list. The responses, tools, processes that worked. Name them so we keep them.

## What went badly
Bullet list. Not people. Processes, tools, absent runbooks, missing alerts.

## Action items
Numbered, owned, dated. Every action item has a single owner and a due date.

1. [ ] <action> — owner: <name> — due: <date>
2. [ ] ...

## Detection / response timing
- **Time to detect:** <symptom-start \u2192 paged>
- **Time to mitigate:** <paged \u2192 impact-stopped>
- **Time to resolve:** <paged \u2192 fully resolved>
```

## 5. Blameless contract

- **No names attached to causes.** Individuals don't cause incidents — systems do. Write "the deploy pipeline allowed" not "Alice pushed a broken".
- **No "should have".** Don't write "Bob should have checked" — write "the review process didn't require checking".
- **Human error is a symptom, not a cause.** If a human pushed the wrong button, the root cause is "the UI allowed the wrong button to be pushed without confirmation".
- **Psychological safety.** The goal is to learn, not to punish. A postmortem that reads like an accusation will make future postmortems worse.

## 6. Action item discipline

- Every action item has **one** owner. "The team" is not an owner.
- Every action item has a **due date**. "Soon" is not a date.
- When completed, check the box and commit. Don't file and forget.
- `wiki-lint` will flag action items older than 30 days that are still unchecked.

## 7. Reference the runbook

If the incident revealed that a runbook was missing or wrong, the action items MUST include creating or updating `runbooks/<slug>/README.md`. A repeat incident without a better runbook is a process failure.
