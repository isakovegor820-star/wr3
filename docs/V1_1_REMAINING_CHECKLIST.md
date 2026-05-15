# wr3 v1.1 Remaining Checklist

Last updated: 2026-05-15

Legend: `done` means implemented or documented to an executable MVP standard.
`partial` means the code boundary exists but needs live provider, production
infra, or dataset validation. `blocked` means external account, legal review, or
customer input is required.

## Current Position

- FR MVP: 15/15 done.
- P0 local MVP: done.
- Localhost-first readiness: done; production accounts intentionally deferred.
- Production readiness: partial, machine-checked at 75.0%.
- Public launch readiness: blocked on legal review, live infrastructure, paid
  provider accounts, and real beta evidence.
- Machine-checkable production readiness is now tracked by
  `npm run production:readiness`.

Latest local evidence:

```text
completion_by_checks=75.0%
counts={'done': 30, 'blocked': 2, 'partial': 8}
blockers=2
tools=Foundry/Anvil installed via Homebrew; Slither/Wake installed in isolated
      artifacts/audit-tools-venv; Aderyn installed via Cargo; Medusa and
      Solana test-validator installed via Homebrew; Trident installed via
      Cargo; ItyFuzz source build attempted and blocked by upstream Rust
      dependency compile error, now explicitly optional by
      infra/sandbox/tool-policy.json until trusted binary/patched build exists
cloudflare=Account ID, scoped API token, D1 database wr3-edge-metadata,
      backup passphrase, awscli, and local encrypted backup/restore drill
      configured. R2 is intentionally skipped in free-only mode because the
      Dashboard requires a payment method to activate it.
benchmark=curated manifest created from external corpora: 144 total cases
      (SmartBugs 49, DeFiHackLabs 60, sealevel-attacks 35) with source commit
      SHAs and content hashes.
sandbox=local policy evidence generated: 9 passed, 0 failed. Real VM/container
      egress test is still required before public launch.
incident=local tabletop artifact generated. Real staging/prod team drill is
      still required before public launch.
secret_manager=no Doppler/1Password/OCI CLI/auth signal on this machine; artifact
      generated without printing secrets.
staging=preflight artifact generated; code/config are ready, real VM host is
      still missing.
curated_benchmark_run=144-case local heuristic smoke benchmark generated; not a
      public quality claim.
beta_validation=0/30 interviews, 0/10 live scans, 0/3 LOI/preorders recorded.
```

The generated artifacts are written to:

- `artifacts/readiness/production_readiness_20260515T090703Z.md`
- `artifacts/benchmarks/curated-benchmark-manifest.json`
- `artifacts/benchmarks/curated-benchmark-run.json`
- `artifacts/readiness/secret_manager_readiness_20260515T090542Z.md`
- `artifacts/readiness/staging_preflight_20260515T090542Z.md`
- `artifacts/readiness/sandbox_container_evidence_20260515T090542Z.md`
- `artifacts/readiness/beta_validation_status_20260515T090543Z.md`

They are local evidence, not marketing material.

## Localhost-First Overlay

The current execution mode is `localhost first`: wr3 should be proven on the
MacBook before connecting domains, production accounts, payments, or live
provider secrets. Production blockers remain tracked below, but they do not
block localhost readiness.

| Local area | Status | Evidence | Remaining localhost work |
| --- | --- | --- | --- |
| Native Postgres/Redis | done | `wr3_local`, Redis PING, API `/ready` storage `postgres_configured` | Optional pgvector later |
| One-command local app | done | `npm run dev:local` | Add Celery toggle when needed |
| Local tools visibility | done | `/v1/tools/status`, `/tools`, readiness route check, 4/4 required tools installed, Trident installed | Resolve optional ItyFuzz build when hybrid fuzzing is needed |
| PoC/fuzzing local mode | done | `npm run poc:local`, `npm run fuzzing:local`, private/skipped artifacts, Foundry/Medusa installed | Install ItyFuzz for hybrid fuzzing |
| Dashboard/emulators/UIs | done | `/dashboard`, `/telegram-emulator`, `/billing`, `/disclosure` | Browser/mobile polish only |
| Local benchmark | done | `npm run benchmark:local`, DeFiHackLabs/SmartBugs/sealevel samples | Expand real datasets later |
| Local readiness command | done | 30 passed, 0 failed, 1 skipped optional | Optional pgvector install |

## Remaining Blocks From The User Pass

| # | Area | Status | Evidence | Remaining blocker |
| --- | --- | --- | --- | --- |
| 1 | Production infrastructure readiness | partial | `infra/`, Postgres schema, pgvector schema, backup/restore scripts, retention sweep, `/health`, `/live`, `/ready`, deployment docs, Cloudflare Account ID/API token/D1 configured, free-only encrypted local backup restored 13 tables, `npm run staging:preflight` artifact | Oracle/Hetzner staging host; R2 only later with billing-enabled account |
| 2 | Secrets and observability | partial, secret-manager blocked | `.env.example`, no-secret readiness output, sensitive scrubber, LLM cost ledger, docs, `npm run secrets:readiness` artifact | Doppler/1Password/OCI secret manager, Sentry project, alert chat, real production metrics sink |
| 3 | Real integrations hardening | partial | Etherscan V2 key configured and verified against Ethereum USDC source; Etherscan-family clients, retries, source metadata, bytecode-only fallback, EIP-1967/proxy metadata, tests | Optional legacy explorer keys, dedicated RPC keys, and sanitized fixtures from live verified contracts |
| 4 | Static analysis productionization | partial | Typed adapters, install detection, structured output preference, raw private artifacts, partial engine behavior, adapter tests, Slither/Wake/Aderyn installed locally | Worker image and real sample corpus validation |
| 5 | LLM triage production hardening | partial | ZDR-required router, untrusted source prompt boundary, deterministic fallback, 4-agent artifact event, consensus/dismissal records | OpenRouter ZDR key, provider eval, cost/quality tuning on real audits |
| 6 | PoC layer completion | partial | Foundry/Anvil installed locally, Foundry worker boundary, max attempts, Team/Pro/deep gating, private artifacts, sandbox policy tests, sandbox container template, local sandbox evidence 9/9 passed | Fork RPC allowlist and egress test in real container/VM |
| 7 | Fuzzing completion | partial | Medusa installed, Medusa/ItyFuzz worker boundary, Team/Pro/deep gating, timeout/allowlist, artifacts; ItyFuzz source build attempted; `infra/sandbox/tool-policy.json` marks ItyFuzz optional with skipped artifacts | Tune real invariant generator; add ItyFuzz only after trusted binary/patched build |
| 8 | Solana beta hardening | partial | Solana beta chain flag, heuristic Anchor detector, sealevel sample fixtures, Trident installed, Solana test-validator installed locally | Real Anchor parser breadth and sealevel subset run |
| 9 | Scoring and calibration | done for MVP, partial for calibration | Deterministic `wr3-score-v0.1`, cap tests, methodology docs, benchmark metrics | Monthly real calibration set and score changelog after real beta data |
| 10 | Reports and UX polish | done for MVP, partial for production | Russian web UI, report disclaimer, score breakdown, partial engine visibility, owner gating, `npm run qa:visual` screenshot regression | Formal a11y QA and broader browser regression |
| 11 | Billing, quotas, access control | partial | Server-side tier policies, degraded mode, manual USDC, Request/Polar intents, refund doc | Live provider accounts and manual ops process |
| 12 | Telegram Mini App and alerts | partial | Real `/tg` Mini App shell, Telegram WebApp script, `/scan`, `/watch`, `/score`, initData auth bridge, webhook tests, menu setup script | Bot token, HTTPS domain/tunnel, Telegram production webhook, TON Connect live integration |
| 13 | Disclosure/legal workflow | partial, legal blocked | Disclosure cases, contact log, gates, human review gate, legal draft docs | Paid legal review before paid/public launch |
| 14 | Benchmark and QA | partial | Local samples, external DeFiHackLabs/SmartBugs/sealevel corpora cloned under `external/benchmarks`, local RAG corpus built, curated 144-case manifest with commit SHAs and content hashes, local 144-case heuristic smoke run, metrics artifact fields, tests | Run full pipeline benchmark with static tools/LLM/PoC layers and publish only reproducible aggregate metrics |
| 15 | Closed beta/public launch readiness | partial, launch blocked | Release gates file, ICP tracker, IR docs, bug bounty setup, launch checklist, local incident tabletop artifact, beta status artifact | 30 interviews, 10 live scans, 3 LOI/preorders, legal review, real staging/prod incident drill, benchmark blog data |

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

Current production readiness command:

```bash
npm run production:readiness
```

Use strict mode only for release gates:

```bash
python3 scripts/production_readiness.py --strict
```

## Highest Priority Next After This Pass

1. Configure one real secret manager flow: Doppler, 1Password service account,
   or OCI Vault. `.env` remains localhost-only.
2. Complete beta validation evidence: 30 interviews, 10 live scans, and 3
   LOI/preorders in `docs/ICP_VALIDATION_TRACKER.md`.
3. Provision Oracle/Hetzner staging with Postgres 17, Redis, Celery, artifact
   key, and encrypted backup/restore drill. R2 stays deferred until a
   billing-enabled account exists.
4. Run the real sandbox worker image with Foundry, Medusa, Trident, optional
   ItyFuzz, no DB write access, and egress allowlist.
5. Run the curated benchmark subsets through the full pipeline and use only
   aggregate, reproducible results in the benchmark blog.
6. Install ItyFuzz only after a trusted binary/patched build is available; until
   then keep it optional and emit skipped artifacts.
7. Get legal review for TOS, privacy, engagement letter, disclosure policy, data
   retention, and refund policy before any paid/public claim.
