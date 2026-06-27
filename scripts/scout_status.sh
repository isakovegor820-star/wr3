#!/usr/bin/env bash
# Quick health dashboard: is the Opus-4.8 triage + scout autopilot actually working?
# Usage:  bash scripts/scout_status.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"

API="${WR3_API:-http://127.0.0.1:8001}"
WEB="${WR3_WEB:-http://127.0.0.1:3001}"
DB="${WR3_DATABASE_NAME:-wr3_local}"
RH="X-WR3-Reviewer: true"

echo "==================== wr3 status ===================="

# 1) API up?
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$API/health" 2>/dev/null)
if [ "$code" = "200" ]; then
  echo "[OK ] API up        $API"
else
  echo "[XX ] API DOWN (health=$code)"
  echo "      start it:  apps/api/.venv/bin/uvicorn wr3_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8001"
  exit 1
fi

# 2) Which model is configured for triage
grep -E '^WR3_LLM_(PROVIDER|MODEL)=|^WR3_SCOUT_AUTOPILOT_ENABLED=' .env 2>/dev/null | sed 's/^/      cfg  /'

# 3) Autopilot running?
curl -s --max-time 8 "$API/v1/monitoring/scout/autopilot" -H "$RH" 2>/dev/null | python3 -c '
import sys,json
try: d=json.load(sys.stdin)
except Exception: print("[XX ] autopilot status unreadable"); sys.exit()
tag="[OK ]" if d.get("running") else "[XX ]"
print(tag,"autopilot",("running" if d.get("running") else "STOPPED"),
      "| cycles="+str(d.get("cycle_count")),
      "| queued_total="+str(d.get("queued_total")),
      "| last_error="+str(d.get("last_error")))
print("      next run at:", d.get("next_run_at"))
'

# 4) Is the model REALLY triaging? (last 30 triage routes: model + success vs fallback)
psql "$DB" -At -F'|' -c "select payload->>'model', coalesce(payload->>'error_type','SUCCESS'), count(*) from (select payload, created_at from audit_events where event_type='llm_triage_route' order by created_at desc limit 30) t group by 1,2 order by 3 desc;" 2>/dev/null | python3 -c '
import sys
rows=[l.split("|") for l in sys.stdin.read().splitlines() if l.strip()]
if not rows: print("[.. ] no triage runs yet"); sys.exit()
tot=sum(int(r[2]) for r in rows); suc=sum(int(r[2]) for r in rows if r[1]=="SUCCESS")
models=", ".join(sorted({r[0] for r in rows}))
print("[OK ]" if tot and suc/tot>=0.8 else "[!  ]",
      f"triage success {suc}/{tot} on {models} (rest = deterministic fallback)")
for r in rows: print(f"        {r[0]:18} {r[1]:22} x{r[2]}")
'

# 5) Recent activity (last hour)
a=$(psql "$DB" -At -c "select count(*) from audit_events where event_type='llm_triage_route' and created_at > now() - interval '1 hour';" 2>/dev/null)
f=$(psql "$DB" -At -c "select count(*) from findings where created_at > now() - interval '1 hour';" 2>/dev/null)
echo "[i  ] last hour:   ${a:-?} audits triaged, ${f:-?} findings produced"

# 6) Latest scouted protocols queued
echo "      recent scouted targets:"
curl -s --max-time 8 "$API/v1/monitoring/scout/autopilot" -H "$RH" 2>/dev/null | python3 -c '
import sys,json
try: d=json.load(sys.stdin)
except Exception: sys.exit()
lr=d.get("last_result") or {}
for a in (lr.get("audits") or [])[:6]:
    print("        -",a.get("chain"),"|",a.get("protocol_name"),"|",str(a.get("address"))[:14])
if not (lr.get("audits")): print("        (none this cycle — likely deduped within 24h, normal)")
'

echo "----------------------------------------------------"
echo "Web UI:  $WEB/command  (вкладка «24/7 Scout» + очередь ревью)   |   $WEB/scout"
echo "Stop:    curl -X POST $API/v1/monitoring/scout/autopilot/stop -H '$RH'"
echo "Run now: curl -X POST $API/v1/monitoring/scout/autopilot/run-now -H '$RH' -d '{}'"
echo "===================================================="
