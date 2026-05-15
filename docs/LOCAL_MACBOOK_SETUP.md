# MacBook Localhost Setup

Goal: run wr3 locally without production accounts, domains, real payment
providers, or live secrets.

## Fresh Start

```bash
cd /Users/egor/Documents/wr3
npm install
python3 -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[dev,worker,secure]"
npm run setup:native
npm run dev:local
```

Open:

```text
http://127.0.0.1:3001
```

## Verify

In another terminal:

```bash
npm run local:readiness
npm run check
npm run benchmark:local
```

Optional tools can be missing. They should appear as skipped/optional, not as
hard failures.

## Native Services

`npm run setup:native` uses Homebrew PostgreSQL and Redis. Docker is not needed
for the local database. Future sandbox workers may use Docker or a VM, but the
current localhost path runs safe local/skipped artifacts.
