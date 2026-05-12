# Safety Policy

wr3 defaults to passive analysis and private reporting.

## Allowed

- Passive analysis of public verified source and user-provided source.
- Local fork or test-validator PoC for owned contracts or explicit scopes.
- Private responsible disclosure.
- Safe Harbor scoped validation with written authorization.

## Blocked

- Live third-party exploitation.
- Mainnet transactions without written authorization.
- Public working exploit release before disclosure windows.
- Public scam/fraud accusations without human/legal review.
- Sending source/findings/PoC/traces to plain logs, analytics, or non-ZDR
  providers.

## MVP Enforcement

- Public pages redact High/Critical findings unless human approved.
- Private audit status, findings, reports, events, and raw-output metadata require
  an owner token or authenticated owner context.
- Raw outputs endpoint returns gated metadata only after owner verification.
- PoC artifacts are private by schema and UI.
- Foundry PoC worker is gated to standard/deep scans and Team/Pro tier; local
  MVP uses a bounded retry loop and only marks a PoC confirmed when an explicit
  confirmation marker is present in the isolated generated test.
- Foundry, Medusa, ItyFuzz, and Trident worker commands must pass
  `SandboxPolicy`: shell metacharacters, `--ffi`, path escapes, and non-allowlist
  RPC hosts are rejected before subprocess execution.
- Deep fuzzing is gated to Team/Pro and records metadata-only skipped results
  until invariant generation and isolated workers are configured.
- Disclosure cases use private reviewer-only timelines and explicit
  7/14/45/90/180-day status gates.
- Webhook test delivery is disabled by default and never includes private
  findings/source/PoC data in payloads; optional signatures cover only safe
  preview payloads.
- Telegram Mini App initData auth requires valid bot-token HMAC, fresh
  `auth_date`, and explicit account consent.
- Safe Harbor registry status is surfaced as metadata only; it does not
  authorize mainnet transactions by itself.
- Artifact vault refuses sensitive artifact writes unless
  `WR3_ARTIFACT_ENCRYPTION_KEY` and the secure crypto extra are configured.
- LLM triage routing requires ZDR by default and wraps source in explicit
  untrusted-source blocks before any provider boundary.
- Prompt-injection markers are detected and flagged.
- Oversized pasted source is rejected through `WR3_MAX_SOURCE_BYTES` before
  ingestion/static/LLM workers can spend resources on it.
- Owners can delete private audit records through `DELETE /v1/audits/{id}`;
  production object-storage deletion must be wired before paid launch.
- Reports use "AI-assisted pre-audit" and "risk score" wording.
- SIWE signature verification and email delivery are explicit configuration
  gates; disabled local paths return limitations instead of pretending to be
  production identity.
