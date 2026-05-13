#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_NAME="${WR3_LOCAL_DB_NAME:-wr3_local}"
POSTGRES_FORMULA="${WR3_POSTGRES_FORMULA:-postgresql@17}"
REDIS_FORMULA="${WR3_REDIS_FORMULA:-redis}"
ENV_FILE="${ROOT_DIR}/.env"

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '[wr3-local] %s\n' "$*"
}

ensure_safe_identifier() {
  local value="$1"
  local label="$2"
  if [[ ! "$value" =~ ^[A-Za-z0-9_]+$ ]]; then
    die "${label} must contain only letters, numbers, and underscores: ${value}"
  fi
}

find_pg_bin() {
  local candidates=(
    "/opt/homebrew/opt/${POSTGRES_FORMULA}/bin"
    "/usr/local/opt/${POSTGRES_FORMULA}/bin"
    "/opt/homebrew/opt/postgresql@17/bin"
    "/usr/local/opt/postgresql@17/bin"
    "/opt/homebrew/opt/postgresql@16/bin"
    "/usr/local/opt/postgresql@16/bin"
    "/opt/homebrew/opt/postgresql/bin"
    "/usr/local/opt/postgresql/bin"
  )
  for dir in "${candidates[@]}"; do
    if [[ -x "${dir}/psql" && -x "${dir}/createdb" ]]; then
      printf '%s\n' "$dir"
      return 0
    fi
  done
  if command -v psql >/dev/null 2>&1 && command -v createdb >/dev/null 2>&1; then
    dirname "$(command -v psql)"
    return 0
  fi
  return 1
}

ensure_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    die "Homebrew is required for native localhost setup. Install it from https://brew.sh/ first."
  fi
}

ensure_postgres() {
  ensure_brew
  if ! find_pg_bin >/dev/null 2>&1; then
    info "Installing ${POSTGRES_FORMULA} with Homebrew..."
    brew install "${POSTGRES_FORMULA}"
  fi

  PG_BIN="$(find_pg_bin)" || die "Postgres binaries were not found after install"
  PSQL="${PG_BIN}/psql"
  CREATEDB="${PG_BIN}/createdb"

  if ! "${PSQL}" -d postgres -Atqc "select 1" >/dev/null 2>&1; then
    info "Starting ${POSTGRES_FORMULA} with brew services..."
    brew services start "${POSTGRES_FORMULA}" >/dev/null
    sleep 3
  fi

  if ! "${PSQL}" -d postgres -Atqc "select 1" >/dev/null 2>&1; then
    die "Postgres is installed but not accepting local socket connections. Check: brew services list"
  fi

  if ! "${PSQL}" -d postgres -Atqc "select 1 from pg_database where datname = '${DB_NAME}'" | grep -qx "1"; then
    info "Creating database ${DB_NAME}..."
    "${CREATEDB}" "${DB_NAME}"
  fi

  info "Applying core schema to ${DB_NAME}..."
  "${PSQL}" -v ON_ERROR_STOP=1 -d "${DB_NAME}" -f "${ROOT_DIR}/infra/postgres/001_core_schema.sql" >/dev/null

  if "${PSQL}" -d "${DB_NAME}" -Atqc "select 1 from pg_available_extensions where name = 'vector'" | grep -qx "1"; then
    info "pgvector available; applying knowledge schema..."
    "${PSQL}" -v ON_ERROR_STOP=1 -d "${DB_NAME}" -f "${ROOT_DIR}/infra/postgres/002_pgvector_knowledge_schema.sql" >/dev/null
  else
    info "pgvector is not installed locally; skipping optional RAG vector schema."
  fi
}

ensure_redis() {
  ensure_brew
  if ! command -v redis-server >/dev/null 2>&1 || ! command -v redis-cli >/dev/null 2>&1; then
    info "Installing ${REDIS_FORMULA} with Homebrew..."
    brew install "${REDIS_FORMULA}"
  fi

  if ! redis-cli ping >/dev/null 2>&1; then
    info "Starting ${REDIS_FORMULA} with brew services..."
    brew services start "${REDIS_FORMULA}" >/dev/null
    sleep 2
  fi

  if ! redis-cli ping >/dev/null 2>&1; then
    die "Redis is installed but not responding to PING. Check: brew services list"
  fi
}

ensure_env_file() {
  local db_url="postgresql:///${DB_NAME}"
  local artifact_key

  if [[ -f "${ENV_FILE}" ]]; then
    info ".env already exists; leaving it unchanged."
    return 0
  fi

  info "Creating local .env from .env.example..."
  cp "${ROOT_DIR}/.env.example" "${ENV_FILE}"
  artifact_key="$(
    python3 - <<'PY'
import base64
import os
print(base64.urlsafe_b64encode(os.urandom(32)).decode("ascii"))
PY
  )"

  python3 - "${ENV_FILE}" "${db_url}" "${artifact_key}" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

env_path = Path(sys.argv[1])
db_url = sys.argv[2]
artifact_key = sys.argv[3]

replacements = {
    "WR3_DATABASE_URL=": f"WR3_DATABASE_URL={db_url}",
    "WR3_TASK_BACKEND=local": "WR3_TASK_BACKEND=local",
    "WR3_ARTIFACT_DIR=.omx/artifacts": "WR3_ARTIFACT_DIR=artifacts/local",
    "WR3_ARTIFACT_ENCRYPTION_KEY=": f"WR3_ARTIFACT_ENCRYPTION_KEY={artifact_key}",
}

lines = []
for line in env_path.read_text(encoding="utf-8").splitlines():
    for prefix, replacement in replacements.items():
        if line.startswith(prefix):
            line = replacement
            break
    lines.append(line)
env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

ensure_safe_identifier "${DB_NAME}" "WR3_LOCAL_DB_NAME"
ensure_postgres
ensure_redis
ensure_env_file

info "Native localhost stack is ready."
info "Database URL: postgresql:///${DB_NAME}"
info "Next: npm run local:readiness"
