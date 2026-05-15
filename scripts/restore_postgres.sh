#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${WR3_DATABASE_URL:-}" ]]; then
  echo "WR3_DATABASE_URL is required" >&2
  exit 2
fi

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/restore_postgres.sh artifacts/backups/wr3-postgres-YYYYMMDDTHHMMSSZ.sql.gz[.enc]" >&2
  exit 2
fi

backup_path="$1"
if [[ ! -f "${backup_path}" ]]; then
  echo "backup file not found: ${backup_path}" >&2
  exit 2
fi

if [[ "${backup_path}" == *.enc ]]; then
  if [[ -z "${WR3_BACKUP_ENCRYPTION_PASSPHRASE:-}" ]]; then
    echo "WR3_BACKUP_ENCRYPTION_PASSPHRASE is required for encrypted backup restore" >&2
    exit 2
  fi
  openssl enc -d -aes-256-cbc -pbkdf2 \
    -pass "env:WR3_BACKUP_ENCRYPTION_PASSPHRASE" \
    -in "${backup_path}" |
    gzip -dc |
    psql "${WR3_DATABASE_URL}" --set ON_ERROR_STOP=on
else
  gzip -dc "${backup_path}" | psql "${WR3_DATABASE_URL}" --set ON_ERROR_STOP=on
fi
