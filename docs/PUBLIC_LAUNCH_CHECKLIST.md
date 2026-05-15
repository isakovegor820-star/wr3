# Public Launch Checklist

Status: launch is blocked until every P0 item is complete.

Current production-readiness evidence:

```text
npm run production:readiness
completion_by_checks=72.5%
blockers=3
```

Localhost readiness is complete, but public launch is not. The remaining P0
gates depend on real staging infrastructure, external legal review, beta
validation, and production operational drills.

## P0 Before Paid/Public Launch

- [ ] Legal review completed for TOS, privacy, engagement letter, disclosure,
  data retention, refund, and AI-assisted audit disclaimer.
- [ ] G4 Safety Gate passed.
- [ ] Production artifact encryption configured.
- [ ] No raw source/findings/PoC in logs, Sentry, analytics, or non-ZDR prompts.
- [ ] Backup encrypted and restore drill completed on staging/prod. R2 is
  deferred while Cloudflare R2 requires billing; encrypted local backup is the
  current free-only fallback.
- [ ] Sandbox worker egress and DB-write isolation verified in real
  container/VM. Local policy evidence is present.
- [ ] Public project page redaction reviewed.
- [ ] Support and incident response contacts published.
- [ ] Benchmark artifact generated and reproducible on curated external subsets.
  Local curated manifest is present; full metric run is still needed.
- [ ] Pricing and refund wording reviewed.

## P1 Before Broad Marketing

- [ ] 30 ICP interviews.
- [ ] 10 live scans.
- [ ] 3 LOI/preorders or equivalent paid signal.
- [ ] One anonymized case study.
- [ ] Telegram bot production webhook configured.
- [ ] UptimeRobot/Sentry/Telegram alerts active.
- [ ] Bug bounty page live or private invite ready. Local incident tabletop
  artifact exists; real team drill is still needed.

## Launch Channels

- Show HN.
- BNB Chain Discord and Telegram.
- X thread.
- Reddit crypto/security communities.
- Product Hunt.
- Direct outreach to friendly projects.

## No-Go Wording

Do not use:

- "guaranteed secure"
- "scam score"
- "AI found every bug"
- "replacement for human auditor"

Use:

- "AI pre-audit"
- "exploitability triage"
- "risk score"
- "no critical findings detected by wr3 vX.Y"
