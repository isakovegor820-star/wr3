#!/usr/bin/env bash
# Run the wr3 API with the Scout autopilot enabled, supervised 24/7.
#
# Two layers of resilience:
#   1. In-process watchdog (ScoutAutopilot) restarts a dead scan loop and pages
#      the owner on a stall.
#   2. This script restarts the whole uvicorn process if it ever exits, with
#      capped exponential backoff — so a crash, OOM, or kill still recovers.
#
# Usage:
#   WR3_DATABASE_URL=postgresql:///wr3_local bash scripts/run_autopilot_supervised.sh
#
# For an unattended boot-time service, install the launchd template instead:
#   infra/launchd/com.wr3.scout.plist.template  (see its header)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
UVICORN="$API_DIR/.venv/bin/uvicorn"          # absolute path: avoids exit-127 after a cwd reset
HOST="${WR3_API_HOST:-127.0.0.1}"
PORT="${WR3_API_PORT:-8001}"
LOG_DIR="${WR3_LOG_DIR:-$ROOT/.wr3-logs}"
mkdir -p "$LOG_DIR"

if [ ! -x "$UVICORN" ]; then
  echo "[supervisor] uvicorn not found at $UVICORN — create the venv first" >&2
  exit 1
fi

# The autopilot must be on for this runner to do its job.
export WR3_SCOUT_AUTOPILOT_ENABLED="${WR3_SCOUT_AUTOPILOT_ENABLED:-true}"

backoff=2
max_backoff=60
echo "[supervisor] starting wr3 API + scout autopilot on $HOST:$PORT (logs: $LOG_DIR)"
while true; do
  start=$(date +%s 2>/dev/null || echo 0)
  "$UVICORN" wr3_api.main:app --app-dir "$API_DIR" --host "$HOST" --port "$PORT" \
    >>"$LOG_DIR/autopilot.out.log" 2>>"$LOG_DIR/autopilot.err.log"
  code=$?
  end=$(date +%s 2>/dev/null || echo 0)
  echo "[supervisor] uvicorn exited code=$code after $((end - start))s — restarting in ${backoff}s" \
    | tee -a "$LOG_DIR/autopilot.err.log" >&2
  # If it ran for a healthy while, reset backoff; otherwise grow it (crash loop guard).
  if [ "$((end - start))" -ge 120 ]; then backoff=2; else backoff=$(( backoff * 2 )); fi
  [ "$backoff" -gt "$max_backoff" ] && backoff=$max_backoff
  i=0
  while [ "$i" -lt "$backoff" ]; do i=$((i + 1)); read -r -t 1 _ </dev/null 2>/dev/null || true; done
done
