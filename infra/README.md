# Infrastructure Stubs

These files are MVP scaffolding plus production-readiness templates. The full
closed-beta runbook lives in `docs/PRODUCTION_DEPLOYMENT.md`.

## Local services

`docker-compose.yml` defines Postgres and Redis for the next persistence/queue
milestone. The current API uses in-memory storage and FastAPI background tasks
as the local queue dispatcher.

To exercise the Celery boundary locally after installing worker extras:

```bash
apps/api/.venv/bin/python -m pip install -e "apps/api[worker]"
docker compose -f infra/docker-compose.yml up -d redis
WR3_TASK_BACKEND=celery apps/api/.venv/bin/celery \
  -A wr3_api.workers.celery_app.celery_app worker --loglevel=info
```

To exercise Postgres persistence locally:

```bash
docker compose -f infra/docker-compose.yml up -d postgres
WR3_DATABASE_URL=postgresql://wr3:wr3_dev_only@127.0.0.1:5432/wr3 \
  apps/api/.venv/bin/uvicorn wr3_api.main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8001
```

`infra/postgres/001_core_schema.sql` is applied automatically by the repository
constructor when `WR3_DATABASE_URL` is configured.

`infra/postgres/002_pgvector_knowledge_schema.sql` is optional and should be
applied only after pgvector is installed. It stores public/reference RAG
documents and 768-dimensional embeddings for Solodit, DeFiHackLabs,
sealevel-attacks, and related datasets.

## Backups and migration drill

Use the scripts below for the Oracle Always Free to Hetzner migration path:

```bash
WR3_DATABASE_URL=postgresql://... scripts/backup_postgres.sh
WR3_DATABASE_URL=postgresql://... scripts/restore_postgres.sh artifacts/backups/wr3-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

The backup script writes gzip-compressed dumps with `0600` permissions, does not
echo the database URL, can encrypt dumps with
`WR3_BACKUP_ENCRYPTION_PASSPHRASE`, and can upload to an R2-compatible bucket
through `WR3_BACKUP_R2_URI` plus AWS-compatible credentials.

## Production target

- Cloudflare Workers for edge API/session metadata.
- FastAPI core API on Oracle Always Free or equivalent VM.
- Postgres + pgvector and Redis on VM.
- Cloudflare R2 for encrypted reports, PoCs, raw outputs, and manifests.
- Sandbox workers without primary DB write access.

## Safety

Do not mount production secrets into sandbox containers. Sandbox workers receive
scoped input bundles and return signed manifests only.
