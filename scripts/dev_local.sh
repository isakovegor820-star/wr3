#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f ".env" ]]; then
  echo "error: .env is missing. Run: npm run setup:native" >&2
  exit 1
fi

if [[ ! -x "apps/api/.venv/bin/python" ]]; then
  echo "error: API virtualenv is missing." >&2
  echo 'Run: python3 -m venv apps/api/.venv && apps/api/.venv/bin/python -m pip install -e "apps/api[dev,worker,secure]"' >&2
  exit 1
fi

if [[ ! -d "node_modules" ]]; then
  echo "error: node_modules is missing. Run: npm install" >&2
  exit 1
fi

mkdir -p artifacts/local

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

set -a
# shellcheck disable=SC1091
source .env
set +a

echo "[wr3-local] API: http://127.0.0.1:8001"
apps/api/.venv/bin/uvicorn wr3_api.main:app \
  --app-dir apps/api \
  --reload \
  --reload-dir apps/api/wr3_api \
  --host 127.0.0.1 \
  --port 8001 &

if [[ "${WR3_TASK_BACKEND:-local}" == "celery" ]]; then
  echo "[wr3-local] Celery worker enabled"
  apps/api/.venv/bin/celery \
    -A wr3_api.workers.celery_app.celery_app \
    --workdir apps/api \
    worker \
    --loglevel=INFO &
else
  echo "[wr3-local] Celery worker skipped; WR3_TASK_BACKEND=${WR3_TASK_BACKEND:-local}"
fi

echo "[wr3-local] Web: http://127.0.0.1:3001"
NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:8001}" npm run dev:web
