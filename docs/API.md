# API Contracts

## Create audit

`POST /v1/audits`

```json
{
  "chain": "base",
  "address": "0x0000000000000000000000000000000000000000",
  "source": "contract Vault { }",
  "requested_depth": "preliminary",
  "visibility": "private",
  "user_intent": "pre_launch_self_check"
}
```

Response:

```json
{
  "audit_id": "uuid",
  "state": "queued",
  "status_url": "/v1/audits/uuid",
  "estimated_wait_seconds": 90,
  "limitations": ["anonymous_owner_token_required_for_private_access"],
  "owner_access_token": "returned-once-local-mvp-token",
  "public_report_token": null
}
```

Private MVP scans can be read with either an authenticated owner session or
`owner_token` query parameter. Production should move owner tokens into secure
HTTP-only session storage. The API schedules processing as a background job, so
callers should poll `GET /v1/audits/{id}` until `completed`, `needs_source`,
`partial`, or `failed`.

## Auth

`GET /health`

Liveness endpoint for uptime probes.

`GET /ready`

Readiness endpoint with non-secret component posture: storage mode, task backend,
artifact encryption status, and LLM provider.

`GET /v1/integrations/status`

Returns sanitized free/API-provider posture for audit ingestion, RPC, Telegram,
LLM, RAG, monitoring, Solana, and roadmap providers. This endpoint
lists env var names and public fallback status, but never returns token values.

`GET /v1/news/hacks?limit=25`

Fetches public DeFiLlama hack metadata without a key and normalizes it for the
news/security-intelligence pipeline. This is public incident data only, not
private customer findings.

`POST /v1/auth/siwe/nonce`

Creates a SIWE nonce and message.

`POST /v1/auth/siwe/verify`

Verifies the nonce/message pair and returns a bearer session. Set
`WR3_SIWE_SIGNATURE_VERIFICATION_ENABLED=true` and install the `secure` extra to
recover and verify the signing address with `eth-account`; otherwise the local
MVP returns an explicit disabled-verification limitation.

`POST /v1/auth/email/request-link`

Returns a local email session stub kept for developer smoke tests.

`POST /v1/auth/email/magic-link`

Creates a 15-minute email magic-link token. When `WR3_EMAIL_DELIVERY_ENABLED` is
false, the response returns a dev verification token instead of pretending an
email was sent.

`POST /v1/auth/email/verify-link`

Consumes the email magic-link token and returns a bearer session.

`POST /v1/auth/telegram/init-data`

Validates Telegram Mini App `initData` using `WR3_TELEGRAM_BOT_TOKEN`, rejects
stale/bad hashes, and requires `explicit_account_consent=true` before issuing a
Telegram session.

## Status

`GET /v1/audits/{id}?owner_token=...`

Returns audit state, progress, score, limitations, and safe summary data.

## Events

`GET /v1/audits/{id}/events?owner_token=...`

Returns the append-only audit event log for state transitions and metadata-only
operational events such as source pull success. Events must not contain private
source, raw findings, or PoC traces.

## Findings

`GET /v1/audits/{id}/findings?owner_token=...`

Owner-only in production. Public callers must never receive raw exploit steps.
`?public=true` returns a redacted public-safe list.

`POST /v1/audits/{id}/findings/{finding_id}/review`

Reviewer-only endpoint to set `human_review_status` to `approved` or
`rejected`. This records a metadata-only `finding_reviewed` event. Public
High/Critical publication still requires separate disclosure/legal gates.

## Report

`GET /v1/audits/{id}/report?format=markdown&owner_token=...`

Returns Markdown or HTML with disclaimer, scope, score breakdown, findings, and
next steps.

## Raw Outputs

`GET /v1/audits/{id}/raw-outputs?owner_token=...`

Returns gated metadata only in the MVP. Raw tool output, private source, PoC
traces, and fuzzer counterexamples must remain owner-gated and encrypted.

## Delete Audit

`DELETE /v1/audits/{id}?owner_token=...`

Owner-only deletion endpoint for private retention/deletion requests. In
Postgres mode, normalized child rows cascade from `audit_jobs`; encrypted object
storage deletion remains a production R2/KMS integration step.

## Public Project

`GET /v1/projects/{chain}/{address}`

Returns public-safe project data. High/Critical findings and PoC artifacts are
redacted unless human-approved disclosure rules allow publication.
The web app exposes this at `/p/<chain>/<address>`.

## Telegram

`POST /v1/telegram/webhook`

Webhook skeleton for `/scan <chain> <address>`. It creates a private
preliminary audit under a Telegram-derived user id and returns a reply payload
with a web status URL. If `WR3_TELEGRAM_WEBHOOK_SECRET` is configured, callers
must pass Telegram's `X-Telegram-Bot-Api-Secret-Token` header.

Real Telegram API delivery is separate from the local command parser and audit
enqueue boundary. The web app also exposes `/tg` as a mobile-first scan surface
for Mini App embedding.

## Watchlist And Webhooks

`POST /v1/watchlist`

Adds an authenticated user's contract watchlist entry. The local MVP returns an
active stub with `monitoring_worker_not_enabled_in_local_mvp`; on-chain workers
are pending.

`POST /v1/webhooks/test`

Validates a webhook URL shape, signs a safe payload when
`WR3_WEBHOOK_SIGNING_SECRET` is configured, and performs delivery only when
`WR3_WEBHOOK_DELIVERY_ENABLED=true`. Test payloads never include private
findings, source, PoC traces, or raw outputs.

## Disclosure Cases

`POST /v1/disclosure-cases`

```json
{
  "finding_id": "wr3-find-uuid",
  "project_contact": "security@example.com",
  "scope_note": "Passive responsible disclosure only"
}
```

Creates a private disclosure-tracking stub with Day 0 contact timeline.
Requires reviewer access in the MVP (`X-WR3-Reviewer: true` dev header or a
future reviewer role).

`GET /v1/disclosure-cases/{id}`

Returns the private disclosure case for reviewers.

`POST /v1/disclosure-cases/{id}/contact-log`

```json
{
  "channel": "email",
  "message": "security@example.com contacted"
}
```

Appends a private contact-log entry.

`POST /v1/disclosure-cases/{id}/advance`

```json
{
  "status": "seal_911_escalation",
  "note": "No response after Day 7"
}
```

Supported statuses map to the MVP disclosure gates:
`private_contact_pending` (Day 7), `seal_911_escalation` (Day 14),
`cve_euvd_notice` (Day 45), `limited_disclosure_allowed` (Day 90),
`full_disclosure_allowed` (Day 180), `resolved`, and `closed`.
