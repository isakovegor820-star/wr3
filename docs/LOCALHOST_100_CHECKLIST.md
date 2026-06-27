# wr3 Localhost 100 Checklist

Last updated: 2026-05-15

Legend: `done` means implemented and verified locally. `partial` means a safe
boundary exists but a real optional tool may be missing. `todo` means planned in
this localhost pass. `blocked` means not applicable without production accounts.

## Current Local Position

- Native PostgreSQL 17: done.
- Redis: done.
- API/Web localhost: done.
- Postgres persistence smoke audit: done.
- Foundry/Anvil Homebrew install: done.
- Slither/Wake isolated audit-tools venv: done.
- Aderyn Cargo install: done.
- Medusa Homebrew install: done.
- Trident Cargo install: done.
- Solana test-validator Homebrew install: done.
- Baseline test suite: done.
- Production accounts/domains: intentionally deferred.

## Localhost-First Stages

| Stage | Area | Status | Evidence | Next local action |
| --- | --- | --- | --- | --- |
| 0 | Preflight and inventory | done | `npm run local:readiness`, `npm run check` | Keep checklist current |
| 1 | Local audit tools | done | `/v1/tools/status`, `/tools`, `test_tools_status.py`, install guide, Foundry/Anvil via Homebrew, Slither/Wake in `artifacts/audit-tools-venv`, Aderyn/Trident via Cargo, Medusa/Solana via Homebrew | Optional ItyFuzz later |
| 2 | PoC local mode | done | `npm run poc:local`, private artifacts, sandbox deny-list tests, Foundry installed | Expand fixture coverage |
| 3 | Fuzzing local mode | done | `npm run fuzzing:local`, Medusa installed, ItyFuzz skipped optional artifact | Install ItyFuzz for hybrid runs |
| 4 | Benchmark local | done | `npm run benchmark:local`, DeFiHackLabs/SmartBugs/sealevel samples | Expand sample size later |
| 5 | Dashboard | done | `/dashboard`, `GET /v1/audits`, filters, retry/delete | UX polish as data grows |
| 6 | Telegram emulator + Mini App | done | `/telegram-emulator`, `/tg`, `/scan`, `/watch`, `/score`, initData bridge | Real BotFather token + HTTPS later |
| 7 | Unrestricted local mode | done | No `/billing` route, no local tier selector, quota path always allows requested depth | Keep feature gates tied to safety, not plans |
| 8 | Disclosure UI | done | `/disclosure`, cases, contact log, timeline/status | External legal review before public launch |
| 9 | UX QA | done | `npm run qa:visual` checks `/`, `/tg`, `/dashboard`, `/disclosure`; `npm run site:smoke` checks real click flows for token check, Bug Bounty, Mini App, dashboard, tools, integrations, disclosure, emulator | Broader browser matrix later |
| 10 | Local readiness 100 | done | `npm run local:readiness` reports 30 passed, 0 failed, 1 skipped optional | Optional pgvector install |
| 11 | Docs final pass | done | Local guides in `docs/` | Keep in sync with code |

## Hard Localhost Definition

Localhost readiness is complete when a developer can run:

```bash
npm run setup:native
npm run dev:local
npm run local:readiness
npm run site:smoke
npm run check
npm run benchmark:local
```

and get a working browser flow for:

1. Create audit.
2. View dashboard.
3. View report/findings/score/raw-output gate.
4. See tool availability.
5. Exercise Telegram emulator.
6. Exercise disclosure and local audit retry flows.
7. Exercise disclosure workflow.
8. See PoC/fuzzing skipped or artifact status without mainnet actions.
