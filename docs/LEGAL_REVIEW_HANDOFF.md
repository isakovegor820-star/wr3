# Legal Review Handoff

Status: external blocker. This file packages what a lawyer must review before
paid/public launch. It is not legal advice and does not make wr3 launch-ready.

## Documents To Review

- `docs/TERMS_OF_SERVICE_DRAFT.md`
- `docs/PRIVACY_POLICY_DRAFT.md`
- `docs/ENGAGEMENT_LETTER_DRAFT.md`
- `docs/RESPONSIBLE_DISCLOSURE_POLICY.md`
- `docs/AI_ASSISTED_AUDIT_DISCLAIMER.md`
- `docs/DATA_RETENTION_DELETION_POLICY.md`
- `docs/REFUND_POLICY.md`
- `docs/SECURITY_AND_LEGAL_GUARDRAILS.md`

## Specific Legal Questions

1. Is the wording safe for an AI-assisted pre-audit product and not presented as
   a replacement for a human security audit?
2. Is the liability cap enforceable for the intended customer jurisdictions?
3. Are passive third-party scans, public project pages, and redacted risk scores
   described safely enough to reduce defamation risk?
4. Do disclosure timelines and SEAL 911 escalation wording avoid unauthorized
   active exploitation?
5. Are data retention, deletion, private source handling, PoC artifact handling,
   and subprocess logs described clearly enough?
6. Is the refund policy enforceable for crypto/manual payments and any fiat MoR
   provider we later connect?
7. Does the engagement letter cover scope, authorization, limitations, and no
   mainnet active actions without explicit written authorization?

## Launch Rule

No paid audit, public High/Critical claim, public exploit detail, or marketing
claim like "secure" may ship until legal review is complete and the reviewed
versions are dated.

## Evidence To Attach

- Latest `npm run production:readiness` artifact.
- Latest sandbox evidence artifact.
- Latest incident tabletop artifact.
- Latest benchmark artifact, using aggregate metrics only.
- A list of supported chains and current limitations.
