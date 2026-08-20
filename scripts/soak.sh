#!/usr/bin/env bash
# Soak: keep runs happening for hours while the stack is deliberately disturbed.
#
#   ./scripts/soak.sh [minutes] [project-name]
#
# What it proves, and how it differs from the phase plan's wording. The plan asks for a
# "multi-hour run"; today one run is one episode, so a single run cannot last hours. The
# property underneath — *no progress is lost while services come and go* — is what this
# exercises, over a continuous stream of scheduled runs instead of one long one. The
# deviation is stated rather than papered over.
#
# Disturbances, rotating: the worker (which takes Chromium with it) and Redis. Both are
# rows in `docs/status/RECOVERY_MATRIX.md`, and both are supposed to cost nothing durable.
#
# Requires the stack up and a model endpoint configured for the worker.
set -euo pipefail
cd "$(dirname "$0")/.."

MINUTES="${1:-120}"
NAME="${2:-Soak $(date -u +%H%M)}"
API="${ROVEQA_API_URL:-http://localhost:8000}"
DISTURB_EVERY_MINUTES="${DISTURB_EVERY_MINUTES:-10}"
TARGET_ORIGIN="${SOAK_TARGET_ORIGIN:-http://frontend:5173}"
LOG="soak-$(date -u +%Y%m%dT%H%M%SZ).log"

say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG"; }

json_field() { python -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }

say "== soak for ${MINUTES}m, disturbing every ${DISTURB_EVERY_MINUTES}m =="

PROJECT=$(curl -sS -X POST "$API/api/v1/projects" -H 'content-type: application/json' \
  -d "{\"name\":\"$NAME\"}" | json_field project_id)
say "project $PROJECT"

curl -sS -X POST "$API/api/v1/projects/$PROJECT/run-policies" -H 'content-type: application/json' \
  -d "{\"allowed_origins\":[\"$TARGET_ORIGIN\"],\"max_duration_seconds\":120,
       \"max_actions\":4,\"max_model_calls\":4,\"set_as_project_default\":true}" >/dev/null

STORY=$(curl -sS -X POST "$API/api/v1/projects/$PROJECT/stories" -H 'content-type: application/json' \
  -d '{"actor":"a QA engineer","goal":"open the application",
       "acceptance_criteria":[{"criterion_id":"ac-loaded",
         "description":"the page loads","verification_hint":"RoveQA"}]}' | json_field story_id)

POLICY=$(docker compose exec -T postgres psql -U agentic -d agentic_qa -tAc \
  "select policy_id from run_policies where project_id='$PROJECT'" | tr -d ' \r')
PLAN=$(curl -sS -X POST "$API/api/v1/stories/$STORY/plans" -H 'content-type: application/json' \
  -d "{\"run_policy_id\":\"$POLICY\"}")
PLAN_ID=$(printf '%s' "$PLAN" | json_field plan_id)
say "plan $PLAN_ID"

# A schedule rather than a loop of `run create`: the runs then come from the same path a
# nightly regression uses, and a restart in the middle is a restart of the real thing.
curl -sS -X POST "$API/api/v1/projects/$PROJECT/schedules" -H 'content-type: application/json' \
  -d "{\"schedule_id\":\"soak\",\"cron\":\"* * * * *\",\"plan_id\":\"$PLAN_ID\",
       \"note\":\"soak\"}" >/dev/null
say "schedule firing every minute"

DEADLINE=$(( $(date +%s) + MINUTES * 60 ))
NEXT_DISTURB=$(( $(date +%s) + DISTURB_EVERY_MINUTES * 60 ))
ROTATION=0

counts() {
  docker compose exec -T postgres psql -U agentic -d agentic_qa -tAc \
    "select count(*) filter (where status in ('completed','failed','cancelled')) || '/' || count(*)
     from runs where project_id='$PROJECT'" | tr -d ' \r'
}

stuck() {
  # Non-terminal and older than five minutes. A run still going after five minutes of a
  # two-minute policy is the symptom this whole exercise is looking for.
  docker compose exec -T postgres psql -U agentic -d agentic_qa -tAc \
    "select count(*) from runs where project_id='$PROJECT'
     and status not in ('completed','failed','cancelled')
     and created_at < now() - interval '5 minutes'" | tr -d ' \r'
}

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  sleep 60
  if [ "$(date +%s)" -ge "$NEXT_DISTURB" ]; then
    case $(( ROTATION % 2 )) in
      0) say "-- restarting worker (takes Chromium with it)"; docker compose restart worker >/dev/null ;;
      1) say "-- flushing and restarting redis";
         docker compose exec -T redis redis-cli FLUSHALL >/dev/null || true
         docker compose restart redis >/dev/null ;;
    esac
    ROTATION=$(( ROTATION + 1 ))
    NEXT_DISTURB=$(( $(date +%s) + DISTURB_EVERY_MINUTES * 60 ))
  fi
  say "terminal/total $(counts)  stuck>5m $(stuck)"
done

say "== done =="
say "final terminal/total $(counts)"
say "stuck runs $(stuck)   (anything but 0 is a finding)"
curl -sS -X DELETE "$API/api/v1/projects/$PROJECT/schedules/soak" -o /dev/null -w 'schedule deleted: %{http_code}\n' | tee -a "$LOG"
say "log: $LOG"
