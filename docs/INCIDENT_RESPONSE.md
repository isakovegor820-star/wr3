# Incident Response

Status: closed beta draft. Requires tabletop exercise before public launch.

## Severity Levels

| Level | Example | Response target |
| --- | --- | --- |
| SEV-0 | Customer 0-day or PoC leaked, production secrets compromised | Triage in 15 min, customer notice in 2h |
| SEV-1 | False public High/Critical claim, auth bypass, artifact access bug | Triage in 30 min, public correction in 1h if needed |
| SEV-2 | Worker outage, failed scans >10%, provider outage | Triage in 2h |
| SEV-3 | Minor UI/API defect | Next sprint |

## First 30 Minutes

1. Freeze deploys.
2. Assign incident commander.
3. Preserve logs without exposing sensitive content.
4. Rotate suspected secrets.
5. Disable affected worker/provider route.
6. Decide whether customer notification is required.

## Customer 0-Day Leak

1. Notify customer within 2 hours.
2. Disable public report/share links for affected audit.
3. Rotate artifact keys if key compromise is possible.
4. Offer mitigation/disclosure help.
5. Open SEAL 911 escalation if the target is in scope and needs urgent help.

## False Public Claim

1. Unpublish or redact page immediately.
2. Human reviewer checks finding.
3. Publish correction within 1 hour if the claim was visible.
4. Add regression test to public redaction/human-review gate.

## Secret Compromise

1. Revoke token in source system.
2. Rotate dependent credentials.
3. Redeploy services.
4. Audit artifact and DB access logs.
5. Document blast radius and follow-up work.

## Postmortem

Every SEV-0/SEV-1 requires:

- Timeline.
- Root cause.
- Customer impact.
- What detected it.
- Why controls failed.
- Action items with owners and dates.
