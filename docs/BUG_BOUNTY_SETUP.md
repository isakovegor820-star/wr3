# wr3 Bug Bounty Setup

Status: draft for Hats Finance or Immunefi. Do not publish until production
scope, payout wallet, and legal terms are reviewed.

## Initial Scope

In scope:

- Auth bypass exposing private audit reports, findings, raw outputs, or PoC
  artifacts.
- Public High/Critical finding disclosure without owner/reviewer authorization.
- Artifact encryption bypass.
- Secret leakage through API, logs, reports, or web UI.
- Sandbox escape from PoC/fuzzing worker to primary DB or production secrets.
- Payment/plan bypass that grants gated artifacts without authorization.

Out of scope:

- Social engineering.
- DDoS or volumetric testing.
- Scans against third-party live contracts without authorization.
- Issues requiring stolen credentials.
- Findings already known in public backlog.

## Starting Payouts

| Severity | Example | Initial payout |
| --- | --- | --- |
| Critical | Private PoC leak or sandbox escape | $500 |
| High | Private report disclosure | $250 |
| Medium | Plan bypass without private data leak | $100 |
| Low | Non-sensitive bug | Thanks/credit |

## Submission Requirements

- Clear reproduction steps.
- Affected endpoint or component.
- No public disclosure before wr3 confirms resolution.
- No access to data beyond the minimum needed to prove impact.

## Launch Blockers

- Multisig or payout wallet ready.
- Responsible disclosure inbox ready.
- Legal terms reviewed.
- Production telemetry can detect bounty-triggered suspicious access.
