#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${WR3_DATABASE_URL:-}" ]]; then
  echo "WR3_DATABASE_URL is required" >&2
  exit 2
fi

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/restore_postgres.sh artifacts/backups/wr3-postgres-YYYYMMDDTHHMMSSZ.sql.gz" >&2
  exit 2
fi

backup_path="$1"
if [[ ! -f "${backup_path}" ]]; then
  echo "backup file not found: ${backup_path}" >&2
  exit 2
fi

gzip -dc "${backup_path}" | psql "${WR3_DATABASE_URL}" --set ON_ERROR_STOP=on
