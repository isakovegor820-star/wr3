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
npm run check
npm run benchmark:mvp
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
and whether the API/web ports are currently open.

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
