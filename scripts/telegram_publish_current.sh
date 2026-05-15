#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f ".env" ]]; then
  echo "error: .env is missing" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${WR3_TELEGRAM_MINI_APP_URL:-}" ]]; then
  echo "error: WR3_TELEGRAM_MINI_APP_URL is missing" >&2
  exit 1
fi

if [[ -z "${NEXT_PUBLIC_API_BASE_URL:-}" ]]; then
  echo "error: NEXT_PUBLIC_API_BASE_URL is missing" >&2
  exit 1
fi

echo "[wr3-telegram] checking Mini App: ${WR3_TELEGRAM_MINI_APP_URL}"
curl -L --fail --silent --show-error --output /tmp/wr3-telegram-mini-app-check.html "${WR3_TELEGRAM_MINI_APP_URL}"

api_check_url="${WR3_TELEGRAM_API_CHECK_URL:-}"
if [[ -z "${api_check_url}" ]]; then
  if [[ "${NEXT_PUBLIC_API_BASE_URL}" == http://127.0.0.1* || "${NEXT_PUBLIC_API_BASE_URL}" == http://localhost* ]]; then
    api_check_url="${WR3_TELEGRAM_MINI_APP_URL%/tg}/api/wr3/health"
  else
    api_check_url="${NEXT_PUBLIC_API_BASE_URL%/}/health"
  fi
fi

echo "[wr3-telegram] checking API: ${api_check_url}"
curl -L --fail --silent --show-error --output /tmp/wr3-telegram-api-check.json "${api_check_url}"

echo "[wr3-telegram] updating menu button"
apps/api/.venv/bin/python scripts/telegram_set_menu_button.py

echo "[wr3-telegram] updating webhook"
apps/api/.venv/bin/python scripts/telegram_set_webhook.py

echo "[wr3-telegram] published"
