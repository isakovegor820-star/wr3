#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${WR3_DATABASE_URL:-}" ]]; then
  echo "WR3_DATABASE_URL is required" >&2
  exit 2
fi

backup_dir="${WR3_BACKUP_DIR:-artifacts/backups}"
backup_target="${WR3_BACKUP_TARGET:-}"
if [[ -z "${backup_target}" ]]; then
  if [[ -n "${WR3_BACKUP_R2_URI:-}" ]]; then
    backup_target="r2"
  else
    backup_target="local"
  fi
fi
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

if [[ "${backup_target}" == "local" ]]; then
  echo "[wr3-backup] local encrypted backup retained; remote upload disabled"
elif [[ "${backup_target}" == "r2" ]]; then
  if [[ -z "${WR3_BACKUP_R2_URI:-}" ]]; then
    echo "WR3_BACKUP_R2_URI is required when WR3_BACKUP_TARGET=r2" >&2
    exit 3
  fi
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws CLI is required for WR3_BACKUP_R2_URI uploads" >&2
    exit 3
  fi
  aws_args=()
  if [[ -n "${AWS_ENDPOINT_URL:-}" ]]; then
    aws_args+=(--endpoint-url "${AWS_ENDPOINT_URL}")
  elif [[ -n "${WR3_BACKUP_S3_ENDPOINT_URL:-}" ]]; then
    aws_args+=(--endpoint-url "${WR3_BACKUP_S3_ENDPOINT_URL}")
  fi
  aws "${aws_args[@]}" s3 cp "${final_output}" "${WR3_BACKUP_R2_URI}/$(basename "${final_output}")"
else
  echo "unsupported WR3_BACKUP_TARGET: ${backup_target}; expected local or r2" >&2
  exit 2
fi

echo "${final_output}"
