#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${WR3_DATABASE_URL:-}" ]]; then
  echo "WR3_DATABASE_URL is required" >&2
  exit 2
fi

backup_dir="${WR3_BACKUP_DIR:-artifacts/backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="${backup_dir}/wr3-postgres-${timestamp}.sql.gz"

mkdir -p "${backup_dir}"
pg_dump "${WR3_DATABASE_URL}" --no-owner --no-privileges | gzip -9 > "${output}"
chmod 600 "${output}"

final_output="${output}"
if [[ -n "${WR3_BACKUP_ENCRYPTION_PASSPHRASE:-}" ]]; then
  encrypted_output="${output}.enc"
  openssl enc -aes-256-cbc -pbkdf2 -salt \
    -pass "env:WR3_BACKUP_ENCRYPTION_PASSPHRASE" \
    -in "${output}" \
    -out "${encrypted_output}"
  chmod 600 "${encrypted_output}"
  rm -f "${output}"
  final_output="${encrypted_output}"
fi

if [[ -n "${WR3_BACKUP_R2_URI:-}" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws CLI is required for WR3_BACKUP_R2_URI uploads" >&2
    exit 3
  fi
  aws s3 cp "${final_output}" "${WR3_BACKUP_R2_URI}/$(basename "${final_output}")"
fi

echo "${final_output}"
