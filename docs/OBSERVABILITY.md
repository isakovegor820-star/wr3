# Observability And Secrets

Status: MVP-safe logging policy plus production setup checklist.

## Secrets Flow

Use Doppler or 1Password Secret Automation as the source of truth. `.env` is
only for local development and must never be committed.

Required production secret classes:

- Database and Redis URLs.
- Explorer API keys.
- OpenRouter ZDR key.
- Artifact encryption key.
- Backup encryption passphrase.
- R2 access key and secret.
- Telegram bot token and webhook secret.
- Webhook signing secret.

## Sensitive Data Rules

Never send these to Sentry, analytics, public logs, or non-ZDR providers:

- Private source code.
- Raw findings.
- PoC code, traces, or exploit steps.
- Fuzzer counterexamples.
- LLM prompt/response bodies.
- API keys, signatures, tokens, owner access tokens.

`wr3_api.services.observability.SensitiveScrubber` redacts nested payloads whose
keys match sensitive markers. Use it before adding any structured event to an
external sink.

## Structured Events

Audit events are append-only records on the audit:

- `source_metadata`
- `source_pulled`
- `llm_triage_route`
- `triage_consensus`
- `bytecode_only_fallback`
- `retention_dry_run`
- `state_transition`

Production sinks should emit counters only:

- Engine runtime by engine/status.
- Engine error type by engine.
- LLM route used, token count, and cost.
- Audit state transitions.
- Scan latency and terminal state.

## LLM Cost Accounting

`LlmCostLedger` records provider/model/tokens/cost without prompt leakage. Store
only:

- provider
- model
- prompt token count
- completion token count
- cost in USD
- audit id
- layer name

Do not store prompt or response body unless paid debug opt-in is explicit and
the payload is encrypted in R2 with short retention.

## Sentry Setup

If Sentry is enabled:

1. Set `WR3_SENTRY_DSN`.
2. Register a before-send hook that passes every event through
   `SensitiveScrubber`.
3. Drop request bodies for `/v1/audits`, `/v1/audits/*/findings`, report,
   raw-output, disclosure, and Telegram webhook routes.
4. Keep retention at 30 to 90 days for beta.

## Alerting

Minimum closed beta monitors:

- UptimeRobot: `/live` every 60 seconds.
- UptimeRobot: `/ready` every 5 minutes.
- Sentry: API 5xx burst.
- Sentry: worker task failures.
- Telegram admin channel: production deploy, backup failure, benchmark failure,
  High/Critical finding requiring review.

## CI Security Checks

Before public launch add required CI jobs:

- Secret scan: `gitleaks` or GitHub secret scanning.
- Dependency audit: `npm audit --production`, `pip-audit` or equivalent.
- License inventory: `npm run license:inventory`.
- Test suite: `npm run check`.
- Benchmark smoke: `npm run benchmark:mvp`.

Open blocker: CI provider secrets and branch protection must be configured in
GitHub before public launch.
