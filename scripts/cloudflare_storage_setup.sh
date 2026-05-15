#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

account_id="${CLOUDFLARE_ACCOUNT_ID:-}"
if [[ -z "${account_id}" ]]; then
  echo "CLOUDFLARE_ACCOUNT_ID is required" >&2
  exit 2
fi

wrangler=(npx --yes wrangler)

echo "[wr3-cloudflare] Checking Cloudflare authentication"
if ! "${wrangler[@]}" whoami >/dev/null; then
  echo "Cloudflare Wrangler is not authenticated." >&2
  echo "Run: npx wrangler login" >&2
  echo "Then rerun: npm run cloudflare:setup-storage" >&2
  exit 3
fi

create_r2_bucket() {
  local bucket="$1"
  echo "[wr3-cloudflare] Ensuring R2 bucket: ${bucket}"
  local list_output
  if ! list_output="$("${wrangler[@]}" r2 bucket list 2>&1)"; then
    echo "[wr3-cloudflare] R2 is not ready for this account yet; skipping bucket ${bucket}." >&2
    echo "[wr3-cloudflare] Cloudflare said:" >&2
    echo "${list_output}" | sed -n '1,8p' >&2
    return 10
  fi

  if echo "${list_output}" | grep -q "\"name\": \"${bucket}\""; then
    echo "[wr3-cloudflare] R2 bucket exists: ${bucket}"
    return
  fi

  local create_output
  if ! create_output="$("${wrangler[@]}" r2 bucket create "${bucket}" 2>&1)"; then
    echo "[wr3-cloudflare] Could not create R2 bucket ${bucket}; continuing with other resources." >&2
    echo "${create_output}" | sed -n '1,8p' >&2
    return 10
  fi
  echo "${create_output}"
}

r2_status="ready"
create_r2_bucket "wr3-prod-artifacts" || r2_status="needs_dashboard_enablement"
create_r2_bucket "wr3-prod-backups" || r2_status="needs_dashboard_enablement"

echo "[wr3-cloudflare] Ensuring D1 database: wr3-edge-metadata"
d1_list_output="$("${wrangler[@]}" d1 list --json 2>&1 || true)"
if echo "${d1_list_output}" | grep -q "\"name\": \"wr3-edge-metadata\""; then
  echo "[wr3-cloudflare] D1 database exists: wr3-edge-metadata"
else
  d1_create_output="$("${wrangler[@]}" d1 create wr3-edge-metadata 2>&1 || true)"
  if echo "${d1_create_output}" | grep -qi "already exists"; then
    echo "[wr3-cloudflare] D1 database already exists: wr3-edge-metadata"
  else
    echo "${d1_create_output}"
    if echo "${d1_create_output}" | grep -qi "ERROR"; then
      exit 11
    fi
  fi
fi

if [[ "${r2_status}" != "ready" ]]; then
  echo "[wr3-cloudflare] R2 setup is PARTIAL. Enable R2 in Cloudflare Dashboard, then rerun this script."
fi

echo "[wr3-cloudflare] Done. Copy the D1 database_id into infra/cloudflare/wrangler.toml when deploying a Worker."
