# wr3 Full Backlog

Statuses: `done`, `in_progress`, `todo`, `blocked`.

Functional requirements are closed for the local MVP contract: **15/15 done**.
Remaining work is tracked under NFR, release gates, legal review, external
provider configuration, and roadmap production hardening.

## Functional Requirements

| ID | Priority | Status | Requirement | Notes |
| --- | --- | --- | --- | --- |
| FR-001 | P0 | done | Create audit by address + chain | `POST /v1/audits` |
| FR-002 | P0 | done | Pull verified source | Source upload + Etherscan-family clients + standard-json unwrap + transient retry policy done; production keys are deployment config |
| FR-003 | P0 | done | Static engines in parallel | Aderyn/Wake/Slither subprocess adapters + EVM/Solana heuristics + raw artifact boundary done |
| FR-004 | P0 | done | LLM triage reduces noise | ZDR router/prompt guardrails + optional OpenRouter four-agent calls + deterministic fallback + consensus done |
| FR-005 | P0 | done | HTML/Markdown report | Includes disclaimer, score, findings, limitations |
| FR-006 | P1 | done | Foundry PoC attempts for top findings | Foundry retry-loop boundary + max attempts + private artifact handling done; real LLM generation remains provider tuning |
| FR-007 | P0 | done | Reproducible scoring | `wr3-score-v0.1` |
| FR-008 | P0 | done | SIWE/email auth | Owner-token/dev-header access, optional SIWE signature verify, email magic-link request/verify, and Telegram initData auth done |
| FR-009 | P0 | done | Unrestricted local access | No plan selector, no depth caps, no PoC/fuzzing tier gates, raw outputs gated only by owner access |
| FR-010 | P1 | removed | Payment/invoice MVP | Removed from localhost product; platform runs without tariffs or payment flows |
| FR-011 | P1 | done | Telegram `/scan` | Webhook command parser + audit enqueue + initData auth bridge + `/tg` scan UI done |
| FR-012 | P2 | done | Public project page | API + web `/p/<chain>/<address>` redacted view done with human-review redaction |
| FR-013 | P1 | done | Benchmark runner | MVP fixture runner with EVM/Solana cases + precision/recall artifact done |
| FR-014 | P1 | done | Disclosure case tracking | Finding review + create/read/contact-log/advance 7/14/45/90/180-day gates done |
| FR-015 | P2 | done | Webhook alerts | Watchlist + safe signed webhook test payloads + opt-in delivery worker path done |

## Non-Functional Requirements

| ID | Priority | Status | Target | Notes |
| --- | --- | --- | --- | --- |
| NFR-001 | P0 | in_progress | 99% beta availability | `/health`, `/live`, `/ready` done; production monitoring pending |
| NFR-002 | P0 | in_progress | p50 <= 90s preliminary | Local inline MVP is fast; production metrics pending |
| NFR-003 | P0 | in_progress | Heavy jobs async | Dispatcher + Celery task boundary done; running Redis/Celery deployment pending |
| NFR-004 | P0 | in_progress | Free scan <= $0.05 | Free depth capped/degraded; no LLM spend in MVP |
| NFR-005 | P0 | in_progress | No plain sensitive logs | Owner gates + artifact vault encryption refusal + scrubber policy done; R2/KMS pending |
| NFR-006 | P0 | done | Score links to versions | Engine/score version in reports |
| NFR-007 | P0 | in_progress | Sandbox worker isolation | Command allowlist enforced in PoC/fuzzing worker boundaries; container egress tests pending |
| NFR-008 | P0 | done | Typed adapter interface | `@wr3/audit-engine` |
| NFR-009 | P1 | in_progress | Oracle to Hetzner in 24h | encrypted pg_dump/R2 upload hooks + restore scripts + runbook added; timed restore drill pending |
| NFR-010 | P1 | in_progress | WCAG AA core flows | Responsive UI done; formal a11y pending |

## Release Gates

| Gate | Status | Condition | Notes |
| --- | --- | --- | --- |
| G1 Architecture freeze | in_progress | State machine, schema, storage, queue confirmed | State/schema/queue/Postgres + optional pgvector boundary done; production deploy pending |
| G2 Signal gate | in_progress | Useful findings on test contracts | MVP fixture benchmark + triage consensus done; real dataset pending |
| G3 PoC economics | in_progress | PoC cost/time within caps | Worker currently skipped unless Team/Pro + future sandbox |
| G4 Safety gate | in_progress | No sensitive logs, sandbox egress, disclaimer | Disclaimer/gating + command sandbox done; container egress verification pending |
| G5 Closed beta | todo | 10 invited projects, <=10% failed scans | Product milestone |
| G6 Public launch | todo | Legal review, benchmark blog, support/IR | Product/legal milestone |

## Risk Register

| ID | Priority | Status | Risk | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | P0 | in_progress | Unauthorized active attack | Passive default, Safe Harbor policy |
| R2 | P0 | in_progress | Defamation from false-positive public claim | Human review flags and redaction |
| R3 | P0 | in_progress | 0-day/customer finding leak | Gated outputs + sensitive artifact write refusal; R2/KMS pending |
| R4 | P1 | todo | Low early revenue | One-shot reports/audit contests pending |
| R5 | P1 | todo | Competitors enter niche | Speed, Solana, TG, benchmark moat |
| R6 | P1 | in_progress | LLM provider disruption | ZDR router/local deterministic fallback done; multi-provider execution pending |
| R7 | P1 | in_progress | Provider ban for security prompts | ZDR-required routing and local fallback done |
| R8 | P1 | todo | Key-person risk | Playbooks/docs in progress |
| R9 | P2 | todo | Solana/Anchor ecosystem churn | Version tracking pending |
| R10 | P1 | todo | Regulatory change | Legal review required |
| R11 | P1 | todo | AI audit commoditization | Distribution/benchmark moat |
| R12 | P2 | todo | Oracle reclaim | Backup/migration pending |
| R13 | P0 | todo | wr3 compromise | Own bounty/external audit pending |
| License/SBOM review | P0 | in_progress | Copyleft or dependency license issue | `npm run license:inventory` CSV generated; legal/license review pending |
| Data deletion | P0 | in_progress | Customer source/findings retained longer than intended | Owner audit delete endpoint + retention sweep + tier retention docs done; encrypted R2 object deletion pending |

## Roadmap

| Item | Priority | Status | Notes |
| --- | --- | --- | --- |
| Postgres + pgvector persistence | P0 | in_progress | JSONB repository + normalized core schema + optional pgvector knowledge schema done; production embedding jobs pending |
| Redis + Celery workers | P0 | in_progress | Dispatcher + worker task files done; production Redis/Celery deployment pending |
| Explorer clients | P0 | done | Etherscan/Base/BscScan/Arbiscan clients with retry policy, metadata capture, proxy hints, and bytecode-only fallback added; production keys are deployment config |
| ZDR LLM triage DAG | P0 | done | Router/prompt guardrail + OpenRouter ZDR request path + four-agent calls + deterministic consensus done |
| Foundry PoC retry loop | P1 | done | Safe retry-loop boundary with max attempts and private artifact handling done |
| Medusa/ItyFuzz fuzzing | P1 | in_progress | Worker boundary + sandbox command allowlist + benchmark metric fields done; real invariant generation/execution pending |
| Solana AST beta | P2 | in_progress | Heuristic Anchor footgun subset done; AST/Trident pending |
| SIWE/email auth | P0 | done | Owner-token/dev-header boundary + optional SIWE verification + email magic-link lifecycle done |
| Billing | P1 | removed | No billing routes, plans, quotas, local tier selector, or payment provider flow |
| Telegram bot + Mini App | P1 | done | `/scan` webhook + initData auth + `/tg` scan UI done |
| News scraper | P2 | in_progress | Source registry + DeFiLlama-like normalization + dedup scaffold done; live fetch workers pending |
| On-chain monitoring | roadmap | todo | Continuous monitoring without plan gates |
| CLI | roadmap | todo | CI/CD integration |
| VS Code extension | roadmap | todo | Olympix-adjacent distribution |
| TON/Aptos/Sui support | roadmap | todo | After EVM/Solana proof |
