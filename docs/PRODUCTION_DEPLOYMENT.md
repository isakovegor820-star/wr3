# Production Deployment Runbook

Status: executable deployment checklist for closed beta staging. Public launch
still requires legal review and a real security pass.

## Target Topology

- Cloudflare: DNS, optional Worker edge facade, D1 for light edge metadata, R2
  for encrypted artifacts and backups.
- Oracle Always Free VM: FastAPI, Celery workers, Postgres 17, pgvector, Redis.
- Sandbox worker host/container: Foundry, Anvil, Medusa, ItyFuzz, Trident, no
  primary DB credentials, egress restricted to allowed fork RPC hosts.
- Hetzner fallback: standby VM that can restore encrypted backup within 24h.

## VM Baseline

```bash
sudo apt-get update
sudo apt-get install -y curl git build-essential postgresql-17 redis-server nginx certbot python3.13 python3.13-venv nodejs npm
sudo systemctl enable --now postgresql redis-server
```

Create a locked service user:

```bash
sudo adduser --system --group --home /opt/wr3 wr3
sudo install -d -o wr3 -g wr3 /opt/wr3/app /opt/wr3/artifacts
```

## Postgres 17 And pgvector

```bash
sudo -u postgres createuser wr3
sudo -u postgres createdb wr3 -O wr3
sudo -u postgres psql -d wr3 -c "alter user wr3 with password 'REPLACE_FROM_DOPPLER';"
sudo -u postgres psql -d wr3 -f infra/postgres/001_core_schema.sql
sudo -u postgres psql -d wr3 -c "create extension if not exists vector;"
sudo -u postgres psql -d wr3 -f infra/postgres/002_pgvector_knowledge_schema.sql
```

Recommended Postgres settings for the Oracle 4 OCPU / 24 GB RAM tier:

```conf
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 16MB
wal_compression = on
checkpoint_completion_target = 0.9
max_connections = 80
```

Template: `infra/postgres/postgresql.production.conf.example`.

## API And Worker

```bash
python3.13 -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[worker,secure]"
npm ci
npm run build
```

Systemd services should run:

- `uvicorn wr3_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8001`
- `celery -A wr3_api.workers.celery_app.celery_app worker --loglevel=info`
- `celery -A wr3_api.workers.celery_app.celery_app beat --loglevel=info`

Templates:

- `infra/systemd/wr3-api.service.example`
- `infra/systemd/wr3-celery.service.example`
- `infra/systemd/wr3-celery-beat.service.example`
- `infra/redis/redis.production.conf.example`

Required production env:

```bash
WR3_ENVIRONMENT=production
WR3_DATABASE_URL=postgresql://wr3:...@127.0.0.1:5432/wr3
WR3_TASK_BACKEND=celery
WR3_CELERY_BROKER_URL=redis://127.0.0.1:6379/0
WR3_CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
WR3_ARTIFACT_ENCRYPTION_KEY=...
WR3_BACKUP_R2_URI=s3://wr3-prod-backups/postgres
WR3_BACKUP_ENCRYPTION_PASSPHRASE=...
```

## Cloudflare Templates

Minimum R2 buckets:

- `wr3-prod-artifacts`: encrypted reports, raw outputs, PoC/fuzzing manifests.
- `wr3-prod-backups`: encrypted Postgres dumps.

Minimum D1 databases:

- `wr3-edge-prod`: edge session/cache metadata only. Do not store private source,
  findings, PoC traces, prompts, or reports in D1.

Cloudflare Worker route is optional in closed beta. If used, it should proxy only
public API traffic and reject raw artifacts or private finding bodies.

Template files:

- `infra/cloudflare/wrangler.toml.example`
- `infra/cloudflare/worker.ts`

## Backup And Restore

Daily encrypted backup:

```bash
WR3_DATABASE_URL=postgresql://... \
WR3_BACKUP_ENCRYPTION_PASSPHRASE=... \
WR3_BACKUP_R2_URI=s3://wr3-prod-backups/postgres \
scripts/backup_postgres.sh
```

Restore drill:

```bash
WR3_DATABASE_URL=postgresql://... scripts/restore_postgres.sh artifacts/backups/wr3-postgres-YYYY.sql.gz
```

The Hetzner fallback plan is:

1. Provision fresh VM from Terraform/manual checklist.
2. Install Postgres 17, Redis, app runtime, and secrets.
3. Pull latest encrypted backup from R2.
4. Decrypt locally, restore with `scripts/restore_postgres.sh`.
5. Point Cloudflare DNS to Hetzner IP.
6. Verify `/live`, `/ready`, a private audit read, and one new scan.

## Health Checks

- `/live`: process liveness for systemd/UptimeRobot.
- `/ready`: dependency posture. Must not echo secret values.
- `/health`: simple service heartbeat.

## Release Deployment Checklist

- [ ] Branch protection and signed commits enabled.
- [ ] Doppler/1Password secret flow configured.
- [ ] `WR3_ARTIFACT_ENCRYPTION_KEY` generated and stored outside git.
- [ ] Postgres schema applied.
- [ ] pgvector schema applied if RAG is enabled.
- [ ] Redis and Celery worker verified.
- [ ] Backup uploaded to R2 and restore drill timed.
- [ ] Sandbox worker cannot reach primary DB.
- [ ] Sandbox egress blocked except configured RPC hosts.
- [ ] UptimeRobot/Sentry/Telegram alerts configured.
- [ ] `npm run check` passes.
- [ ] Benchmark subset artifact generated.
