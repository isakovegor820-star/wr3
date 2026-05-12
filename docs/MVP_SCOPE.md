# MVP Scope

The MVP is an EVM-first pre-audit scanner. It is not a full human audit,
insurance product, active rescue system, or public accusation engine.

## Included

- Chain/address/source audit creation.
- Source-present ingestion path and needs-source fallback.
- Aderyn/Wake subprocess wrappers or skipped stubs.
- Solana beta heuristic adapter for a small Anchor footgun subset.
- Unified finding schema.
- Deterministic triage fallback plus optional ZDR OpenRouter four-agent triage.
- Reproducible scoring.
- Markdown/HTML report skeleton.
- Scan UI and report UI.
- Safety/legal guardrails.
- Owner-token/dev-header auth boundary, optional SIWE signature verification,
  and email magic-link request/verify lifecycle.
- Server-side tier policy for Free/Hobby/Team/Pro with depth caps and degraded
  quota mode.
- Sandbox command allowlist for generated Foundry/Medusa/ItyFuzz commands.
- Local deterministic RAG scaffold and optional pgvector schema.
- Telegram `/scan`, billing, disclosure, watchlist, webhook delivery toggle, and
  benchmark runner.
- Telegram initData verification for Mini App auth bridge.
- Mobile-first `/tg` web route for Telegram Mini App top-of-funnel scan flow.
- Safe Harbor registry hook for public project pages.
- Readiness endpoint for uptime/deploy checks.
- Tests for scoring, schemas, state machine, adapters, and API smoke.

## Deferred To P1/P2

- Production email provider delivery and reviewer/user role management.
- Redis/Celery deployment and async worker operations.
- Provider-tuned LLM prompts and cost calibration.
- Real Medusa/ItyFuzz/Trident fuzzing execution.
- TON billing integration and production Telegram alert delivery.
- Full DeFiHackLabs/SmartBugs/sealevel benchmark dataset wiring.

## Explicit Non-Goals

- Guaranteed "secure" verdict.
- Mainnet exploitation.
- Public scam/fraud labels.
- Enterprise audit replacement.
- Token/fundraising mechanics.
