# wr3 v1.1 Remaining Checklist

Last updated: 2026-05-12

Legend: `done` means implemented or documented to an executable MVP standard.
`partial` means the code boundary exists but needs live provider, production
infra, or dataset validation. `blocked` means external account, legal review, or
customer input is required.

## Current Position

- FR MVP: 15/15 done.
- P0 local MVP: done.
- Production readiness: partial.
- Public launch readiness: blocked on legal review, live infrastructure, paid
  provider accounts, and real beta evidence.

## Remaining Blocks From The User Pass

| # | Area | Status | Evidence | Remaining blocker |
| --- | --- | --- | --- | --- |
| 1 | Production infrastructure readiness | partial | `infra/`, Postgres schema, pgvector schema, backup/restore scripts, retention sweep, `/health`, `/live`, `/ready`, deployment docs | Live Oracle VM, Cloudflare D1/R2 account, timed Hetzner restore drill |
| 2 | Secrets and observability | partial | `.env.example`, no-secret readiness output, sensitive scrubber, LLM cost ledger, docs | Sentry project, Doppler workspace, alert chat, real production metrics sink |
| 3 | Real integrations hardening | partial | Etherscan-family clients, retries, source metadata, bytecode-only fallback, EIP-1967/proxy metadata, tests | Real API keys and explorer fixtures from live verified contracts |
| 4 | Static analysis productionization | partial | Typed adapters, install detection, structured output preference, raw private artifacts, partial engine behavior, adapter tests | Installed Aderyn/Wake/Slither in production worker image and real sample corpus |
| 5 | LLM triage production hardening | partial | ZDR-required router, untrusted source prompt boundary, deterministic fallback, 4-agent artifact event, consensus/dismissal records | OpenRouter ZDR key, provider eval, cost/quality tuning on real audits |
| 6 | PoC layer completion | partial | Foundry worker boundary, max attempts, Team/Pro/deep gating, private artifacts, sandbox policy tests | Foundry/Anvil installed in sandbox image, fork RPC allowlist, egress test in container |
| 7 | Fuzzing completion | partial | Medusa/ItyFuzz worker boundary, Team/Pro/deep gating, timeout/allowlist, artifacts | Real invariant generator tuning and installed fuzzers |
| 8 | Solana beta hardening | partial | Solana beta chain flag, heuristic Anchor detector, sealevel sample fixtures, Trident boundary | Real Anchor parser breadth, Trident install, test-validator CI image |
| 9 | Scoring and calibration | done for MVP, partial for calibration | Deterministic `wr3-score-v0.1`, cap tests, methodology docs, benchmark metrics | Monthly real calibration set and score changelog after real beta data |
| 10 | Reports and UX polish | done for MVP, partial for production | Russian web UI, report disclaimer, score breakdown, partial engine visibility, owner gating | Formal mobile/a11y QA and browser screenshot regression |
| 11 | Billing, quotas, access control | partial | Server-side tier policies, degraded mode, manual USDC, Request/Polar intents, refund doc | Live provider accounts and manual ops process |
| 12 | Telegram Mini App and alerts | partial | `/scan`, `/watch`, `/score` flow boundary, initData auth, webhook tests, `/tg` page | Bot token, Telegram production webhook, TON Connect live integration |
| 13 | Disclosure/legal workflow | partial, legal blocked | Disclosure cases, contact log, gates, human review gate, legal draft docs | Paid legal review before paid/public launch |
| 14 | Benchmark and QA | partial | MVP runner, SmartBugs/sealevel sample fixtures, metrics artifact fields, tests | DeFiHackLabs clone, SmartBugs corpus, sealevel full subset, CI runtime budget |
| 15 | Closed beta/public launch readiness | partial, launch blocked | Release gates file, ICP tracker, IR docs, bug bounty setup, launch checklist | 30 interviews, 10 live scans, 3 LOI/preorders, legal review, benchmark blog data |

## Zero-Cost Procurement Pass

Status: done for research and local planning. The source map is in
`docs/ZERO_COST_RESOURCE_PLAN.md`; account setup is tracked in
`docs/FREE_ACCOUNT_SETUP_CHECKLIST.md`; dataset acquisition is tracked in
`docs/FREE_DATASET_ACQUISITION.md`; free legal templates are mapped in
`docs/FREE_LEGAL_RESOURCE_MAP.md`.

Current local readiness command:

```bash
npm run free-tier:readiness
```

It currently reports no production accounts configured in this local shell, which
is expected until the owner creates the free accounts and injects secrets through
Doppler/OCI Vault.

## Highest Priority Next After This Pass

1. Provision Oracle VM staging with Postgres 17, Redis, Celery, artifact key, and
   encrypted backups to R2.
2. Run real explorer fixture tests against Ethereum/Base/BSC/Arbitrum with API
   keys and store sanitized fixtures.
3. Build sandbox worker image with Foundry, Medusa, ItyFuzz, Trident, no DB
   write access, and egress allowlist.
4. Run benchmark subsets: MVP fixtures, SmartBugs sample, sealevel sample, then
   DeFiHackLabs 100-case subset.
5. Get legal review for TOS, privacy, engagement letter, disclosure policy, data
   retention, and refund policy before any paid/public claim.
