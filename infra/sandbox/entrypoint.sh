#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${WR3_DATABASE_URL:-}" ]]; then
  echo "refusing to start sandbox with WR3_DATABASE_URL set" >&2
  exit 64
fi

if [[ -n "${DOPPLER_TOKEN:-}" || -n "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  echo "refusing to start sandbox with secret-manager token env" >&2
  exit 64
fi

export PATH="/opt/wr3/.venv/bin:${PATH}"

if [[ "$#" -eq 0 ]]; then
  exec python -m wr3_api.workers.tasks
fi

exec "$@"
