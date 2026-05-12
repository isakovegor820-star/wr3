# wr3

AI-assisted smart contract pre-audit platform for small EVM and Solana teams.

This repository implements the local MVP slice described in
`docs/TZ_TRACEABILITY.md`: an EVM-first scanner with a typed audit state
machine, normalized findings, transparent scoring, a FastAPI core API, and a
Next.js web app. Solana, Foundry PoC attempts, fuzzing, billing, Telegram,
RAG/news, and benchmark automation are implemented behind safe typed
boundaries, with external provider execution disabled unless configured.

## What is implemented now

- Monorepo layout: `apps/api`, `apps/web`, `packages/shared`.
- Required workspace packages: `packages/types`, `packages/scoring`,
  `packages/audit-engine`, `packages/shared`.
- Unified finding schema and audit job states.
- Reproducible `wr3-score-v0.1` scoring with the public MVP weights.
- FastAPI endpoints for audit creation, status, findings, reports, retry, and
  public project summaries.
- Optional Postgres persistence behind `WR3_DATABASE_URL`; in-memory storage
  remains the zero-config default. Audit events, engine runs, and findings are
  also written to normalized tables when Postgres is enabled.
- Server-side Free/Hobby/Team/Pro tier policy with depth caps and degraded quota
  mode.
- One-shot audit package catalog for quickcheck/PoC/deep AI-assisted reports.
- Billing plan API, manual USDC payment intents, Request Finance/Polar checkout
  intent contracts, and reviewer-only subscription confirmation.
- Telegram `/scan` webhook skeleton that queues private preliminary audits.
- Telegram Mini App initData auth validation with explicit account consent.
- Watchlist and signed webhook test delivery. Network delivery is off by
  default and can be enabled with `WR3_WEBHOOK_DELIVERY_ENABLED=true`.
- Safe Harbor registry hook for public project status.
- Public project page at `/p/<chain>/<address>` backed by redacted project API.
- Source metadata capture: source hash, verified timestamp, explorer metadata,
  bytecode-only limited mode, and EIP-1967/proxy hints.
- Gated raw-output metadata endpoint and responsible-disclosure case stub.
- Reviewer-only responsible-disclosure timeline with 7/14/45/90/180-day gates.
- Engine adapter interface plus EVM heuristic, Aderyn CLI, and Wake CLI adapter
  shells. External tools are subprocess-only to respect license boundaries.
- Foundry PoC retry-loop boundary with tier/sandbox gates, max-attempt budget,
  private artifact storage, and no fake exploit confirmation.
- AI-fuzzing worker boundary for Medusa/ItyFuzz with sandbox command validation.
- Solana beta heuristic adapter for account validation, signer, PDA,
  `init_if_needed`, and CPI/PDA seed footguns.
- Local deterministic RAG scaffold plus optional pgvector schema.
- News-source registry, DeFiLlama-like incident normalization, and dedup
  scaffold.
- Postgres backup/restore scripts for the Oracle-to-Hetzner portability path,
  with optional encryption and R2-compatible upload.
- Tier-based retention sweep command and Celery task.
- Safety gates for prompt-injection markers, third-party scans, public
  visibility, and raw exploit access.
- Optional OpenRouter four-agent triage path that requests ZDR routing and
  falls back to deterministic triage when disabled or unavailable.
- Multi-agent triage consensus for severity, false-positive, business-logic,
  and cross-contract passes.
- Next.js scan and report UI with progress stages, score breakdown, paywall
  states, and partial-stage messaging.
- Unit and API tests for scoring, state transitions, safety, and audit flow.

## Quick start

Install JavaScript dependencies:

```bash
npm install
```

Install Python dependencies:

```bash
python3 -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[dev]"
```

Optional local Postgres:

```bash
docker compose -f infra/docker-compose.yml up -d postgres
export WR3_DATABASE_URL=postgresql://wr3:wr3_dev_only@127.0.0.1:5432/wr3
```

Run the API:

```bash
apps/api/.venv/bin/uvicorn wr3_api.main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8001
```

Run the web app:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 npm run dev:web
```

Run checks:

```bash
npm run check
npm run benchmark:mvp
```

For the fuller implementation map, see:

- `docs/ARCHITECTURE.md`
- `docs/MVP_SCOPE.md`
- `docs/BACKLOG.md`
- `docs/V1_1_REMAINING_CHECKLIST.md`
- `docs/ZERO_COST_RESOURCE_PLAN.md`
- `docs/FREE_ACCOUNT_SETUP_CHECKLIST.md`
- `docs/FREE_DATASET_ACQUISITION.md`
- `docs/FREE_LEGAL_RESOURCE_MAP.md`
- `docs/PRODUCTION_DEPLOYMENT.md`
- `docs/OBSERVABILITY.md`
- `docs/SAFETY.md`

## Scope guardrails

wr3 is a pre-audit and exploitability triage tool. It must not be marketed as a
replacement for a human audit, must not publish high-risk claims without human
review, and must not provide active exploitation guidance for live third-party
systems. See `docs/SECURITY_AND_LEGAL_GUARDRAILS.md`.
