# wr3 MVP Traceability

This file maps the supplied technical specification to the repository scaffold.
The source document is intentionally broader than a single implementation pass:
it describes a 14-week closed beta path plus a 20-week public launch. This repo
now closes the 15 functional requirements for the local MVP contract and keeps
paid-launch operations, legal review, provider accounts, and roadmap work under
NFR/release-gate tracking.

## P0/P1 requirements covered

| Spec item | Status | Implementation |
| --- | --- | --- |
| FR-001 create audit by address and chain | Implemented | `POST /v1/audits` |
| FR-002 verified source pull fallback | Implemented | Source accepted directly; Etherscan-family source pullers with retry; standard-json source unwrap done |
| FR-003 static engines parallel | Implemented | `EngineAdapter`, Aderyn/Wake/Slither subprocess wrappers, EVM/Solana heuristic fallback, raw artifact boundary |
| FR-004 LLM triage | Implemented | ZDR route metadata, untrusted-source prompt wrapping, optional OpenRouter four-agent calls, deterministic fallback, multi-agent consensus |
| FR-005 HTML/Markdown report | Implemented | `ReportRenderer` plus `/v1/audits/{id}/report` |
| FR-006 Foundry PoC for top findings | Implemented | Safe Foundry retry-loop boundary with max attempts, tier/sandbox gates, private artifact storage, and no fake confirmations |
| FR-007 reproducible scoring | Implemented | `wr3-score-v0.1` in Python and TypeScript |
| FR-008 auth via SIWE/email | Implemented | Owner token/dev-header auth, optional SIWE signature verification, email magic-link lifecycle, Telegram initData bridge |
| FR-009 tier access control | Implemented | Server-side tier policy, depth caps, degraded quotas, PoC gates, owner/tier-gated raw outputs |
| FR-010 payment/invoice MVP | Implemented | Plan/package API, manual USDC intent, Request/Polar checkout intent contracts, reviewer subscription confirmation |
| FR-011 Telegram `/scan` | Implemented | Webhook parser queues private preliminary scans; initData auth bridge; `/tg` Mini App scan UI |
| FR-012 public project page | Implemented | Redacted API and web `/p/<chain>/<address>` page with Safe Harbor hook |
| FR-013 benchmark runner | Implemented | MVP EVM/Solana fixture runner writes precision/recall artifact |
| FR-014 disclosure case tracking | Implemented | Reviewer-only create/read/contact-log/advance workflow with 7/14/45/90/180 gates |
| FR-015 webhook alerts | Implemented | Watchlist plus signed safe webhook test payloads and opt-in delivery path |
| Solana beta scanner | Partial | Heuristic Anchor/Rust footgun adapter; AST parser and Trident pending |
| Medusa/ItyFuzz fuzzing | Partial | Deep Team/Pro fuzzing worker boundary and sandbox checks; real execution pending |
| News pipeline | Partial | Source registry, DeFiLlama-like normalization, severity/category inference, dedup scaffold |

## NFR coverage added in current scaffold

| Spec item | Status | Implementation |
| --- | --- | --- |
| NFR-003 heavy jobs async | Partial | Dispatcher + Celery task boundary; production Redis/Celery deployment pending |
| NFR-005 private data controls | Partial | Owner-gated private endpoints and artifact vault encryption refusal; R2/KMS pending |
| NFR-007 sandbox isolation | Partial | Generated command allowlist rejects shell syntax, dangerous flags, path escapes, and non-allowlist RPC hosts |
| NFR-009 portability | Partial | Postgres backup/restore scripts added; timed migration drill pending |
| NFR-001 availability posture | Partial | `/health` and `/ready`; production monitoring pending |
| Data model persistence | Partial | Postgres JSONB repositories plus normalized audit_events/engine_runs/findings writes and optional pgvector knowledge schema |

## Non-negotiable safety decisions

- Reports include an AI-assisted pre-audit disclaimer.
- Public visibility cannot expose High/Critical findings without human review.
- Public callers never receive raw PoC or step-by-step exploit artifacts.
- Contract source is treated as untrusted input.
- External GPL/AGPL tools are represented as subprocess adapters, not linked
  libraries, and generated tool commands pass `SandboxPolicy`.

## Next implementation milestones

1. Wire production R2/KMS artifact deletion and encrypt-or-redact all sensitive Postgres payload fields before paid launch.
2. Calibrate OpenRouter/local-model prompts and cost caps on live contracts.
3. Replace fuzzing skipped workers with isolated Medusa/ItyFuzz/Trident execution and invariant generation.
4. Add persistent Redis/Postgres quota counters and production reviewer roles.
5. Expand benchmark runner to DeFiHackLabs, SmartBugs, EVMbench, and sealevel fixtures.
