# Local Readiness Command

Run:

```bash
npm run local:readiness
```

The command returns JSON with `readiness`, `summary`, and per-check evidence.

For the browser product flow, run:

```bash
npm run site:smoke
```

This opens the localhost site with Playwright and checks the main token risk
flow, Bug Bounty safe scan flow, Mini App scan/Bounty flows, dashboard, tools,
integrations, disclosure, and Telegram emulator routes.

## Hard Checks

- `.env` exists.
- Node dependencies are installed.
- API virtualenv exists.
- Redis responds.
- PostgreSQL connects.
- Core schema tables exist.
- Artifact encryption key exists.
- API/web ports are open.
- Benchmark fixtures exist.
- Basic local scan can be created.
- Core localhost routes return HTTP 200.
- Core site actions work in the browser through `npm run site:smoke`.
- `npm run poc:local` and `npm run fuzzing:local` complete.

## Skipped/Optional Checks

- `pgvector` is optional until RAG is expanded beyond local samples.
- Foundry, Slither, Aderyn, Wake, Medusa, ItyFuzz, and Trident may be missing.
  Missing tools are surfaced as optional/skipped because the platform must keep
  working with deterministic local fallbacks.
- `benchmark:local` is intentionally treated as a long-running manual check by
  default. Run `WR3_READINESS_RUN_LONG_BENCHMARKS=true npm run local:readiness`
  or `npm run benchmark:local` when you want the full benchmark gate.
