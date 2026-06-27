# Development

## Native localhost stack

wr3 is developed locally without production accounts. The recommended MacBook
stack is native Homebrew services:

- PostgreSQL for persistent audits, findings, reports, disclosure cases, and
  benchmark metadata.
- Redis for Celery once background workers are enabled.
- FastAPI in `apps/api/.venv`.
- Next.js through npm workspaces.
- Local encrypted artifacts under `artifacts/local`.

Docker is optional for future sandbox isolation. It is not required for the
database path.

## First-time setup

```bash
npm install
python3 -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[dev,worker,secure]"
npm run setup:native
npm run local:readiness
npm run site:smoke
npm run check
npm run benchmark:local
```

`npm run setup:native` installs/starts Homebrew PostgreSQL and Redis when they
are missing, creates the `wr3_local` database, applies
`infra/postgres/001_core_schema.sql`, applies the optional pgvector migration
only when pgvector is installed, and creates a local `.env` when one does not
already exist.

The local database URL is:

```bash
WR3_DATABASE_URL=postgresql:///wr3_local
```

This uses the local Postgres socket and the current macOS user, which avoids
putting database passwords into localhost config.

## Run services

```bash
npm run dev:local
```

For split terminals:

```bash
npm run dev:api
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 npm run dev:web
```

Celery is optional on localhost. Set `WR3_TASK_BACKEND=celery` in `.env` only
after Redis is running and `apps/api[worker]` is installed. Otherwise the API
uses FastAPI local background tasks.

## Local readiness

```bash
npm run local:readiness
```

The readiness command checks `.env`, Node dependencies, API venv, Redis,
Postgres connectivity, core schema tables, optional pgvector, artifact storage,
tool-status API, benchmark fixtures, safe local scan flow, key web routes, and
the local PoC/fuzzing/benchmark commands.

```bash
npm run site:smoke
```

The site smoke command drives the actual browser UI: token risk check, Bug
Bounty safe scan, Mini App scan/Bounty, dashboard, tools, integrations,
disclosure, and Telegram emulator. It writes screenshots and a JSON report to
`artifacts/site-smoke/`.

See also:

- `docs/LOCAL_MACBOOK_SETUP.md`
- `docs/AUDIT_TOOLS_INSTALL.md`
- `docs/POC_LOCAL_MODE.md`
- `docs/FUZZING_LOCAL_MODE.md`
- `docs/LOCAL_BENCHMARK.md`
- `docs/TELEGRAM_MINI_APP.md`
- `docs/TELEGRAM_EMULATOR.md`
- `docs/BILLING_MOCK.md`
- `docs/DISCLOSURE_UI.md`
- `docs/LOCAL_READINESS.md`

## Adapter policy

Adapters must implement:

```ts
type EngineAdapter = {
  name: string;
  version(): Promise<string>;
  supports(input: AuditInput): boolean;
  run(input: NormalizedSource, opts: EngineRunOptions): Promise<EngineRunResult>;
  normalize(raw: unknown): FindingCandidate[];
};
```

When a tool supports JSON or SARIF, parse that format. Human-readable stdout can
only be stored as a debug artifact.
