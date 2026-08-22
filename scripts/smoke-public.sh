#!/usr/bin/env bash
# Gate 4: point the agent at real public sites nobody used to build it.
#
#   ./scripts/smoke-public.sh [url ...]
#
# Every serious defect in this project was invisible against the local fixture — which
# answers in three milliseconds, completely, and never shows a cookie banner — and
# appeared the first time the agent met a site chosen by somebody else. So the sites
# here are deliberately not ours.
#
# Read-only, and small. Each run may take a handful of actions and go nowhere but the
# origin it was given; a navigation is the only action a read-only policy permits, so
# nothing here can submit a form or press a button on somebody else's website. It is
# a few page loads — less than opening the site in a browser and clicking around.
#
# **No model is used and none is configured.** Exploration decides what to try from what
# the page offers, so a site sweep costs zero inference. Running it with no endpoint at
# all is what makes "zero model calls" a structural fact rather than a measurement that
# happened to come out at zero.
set -euo pipefail
cd "$(dirname "$0")/.."

API="${ROVEQA_API_URL:-http://localhost:8000}"
ACTIONS="${SMOKE_MAX_ACTIONS:-8}"
WAIT_SECONDS="${SMOKE_WAIT_SECONDS:-180}"

# Two archetypes, and one of them has a consent banner — which the phase plan asks for
# because a banner is the first thing an agent meets on the public web and nothing in
# the system closes one yet. Seeing it fail here is the point.
DEFAULT_SITES=(
  "https://example.com"
  "https://www.iana.org"
)
SITES=("$@")
[ ${#SITES[@]} -eq 0 ] && SITES=("${DEFAULT_SITES[@]}")

say() { printf '\n== %s\n' "$*"; }
field() { python -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }

psql() { docker compose exec -T postgres psql -U agentic -d agentic_qa -tAc "$1" | tr -d '\r'; }

sweep() {  # $1 = origin
  local origin="$1" project run status
  say "$origin"

  project=$(curl -sS -X POST "$API/api/v1/projects" -H 'content-type: application/json' \
    -d "{\"name\":\"smoke $origin\"}" | field project_id)
  curl -sS -X POST "$API/api/v1/projects/$project/run-policies" \
    -H 'content-type: application/json' \
    -d "{\"allowed_origins\":[\"$origin\"],\"max_duration_seconds\":150,
         \"max_actions\":$ACTIONS,\"max_model_calls\":0,
         \"destructive_actions\":false,\"set_as_project_default\":true}" >/dev/null

  # `max_model_calls: 0` is not a precaution here, it is the claim. If anything asked for
  # a model this run would stop, and there is no endpoint for it to ask.
  run=$(curl -sS -X POST "$API/api/v1/runs" -H 'content-type: application/json' \
    -H "Idempotency-Key: smoke-$project" \
    -d "{\"project_id\":\"$project\",\"explore\":true}" | field run_id)
  echo "run $run"

  local waited=0
  until [ "$waited" -ge "$WAIT_SECONDS" ]; do
    status=$(psql "select status from runs where run_id='$run'")
    case "$status" in completed|failed|cancelled) break ;; esac
    sleep 5
    waited=$((waited + 5))
  done

  echo "  status   $(psql "select status from runs where run_id='$run'")"
  echo "  verdict  $(psql "select coalesce(verdict,'-') from runs where run_id='$run'")"
  echo "  states   $(psql "select count(*) from explored_states where run_id='$run'")"
  echo "  stopped  $(psql "select coalesce(stop_reason,'-') from exploration_runs where run_id='$run'")"
  echo "  actions  $(psql "select count(*) from run_events where run_id='$run' and type='run.action.taken'")"
  echo "  observed $(psql "select count(*) from observed_failures where run_id='$run'")"

  psql "select '  · ' || route || '  ' || coalesce(title,'(no title)')
        from explored_states where run_id='$run' order by id limit 10"
  psql "select '  ! ' || kind || '  ' || left(detail, 90)
        from observed_failures where run_id='$run' order by id limit 5"
}

say "no model endpoint is configured for the worker — a sweep must not need one"
docker compose exec -T worker printenv | grep -E '^VLLM_(BASE_URL|MODEL)=' || true

for site in "${SITES[@]}"; do
  sweep "$site"
done

say "done"
