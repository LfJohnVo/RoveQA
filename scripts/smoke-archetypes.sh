#!/usr/bin/env bash
# Many sites, many shapes, and a machine-readable result for each.
#
#   ./scripts/smoke-archetypes.sh [out.json]
#
# `smoke-public.sh` answers "does it work against a real site". This answers the harder
# question: does it work against sites that are *different from each other*. Every serious
# defect in this project was invisible against the local fixture — which answers in three
# milliseconds, completely, and never shows a cookie banner — and appeared the first time
# the agent met something somebody else built.
#
# The archetypes are chosen to disagree: a page with almost nothing on it, a deep
# institutional site, a government service behind a consent wall, and a service built to
# be called by machines. Each is read-only and a handful of navigations — less than a
# person opening the site and clicking around.
#
# **No model endpoint is needed.** A traversal decides from what the page offers, so this
# whole suite costs zero inference. Running it against a worker with no model configured
# is what makes that structural rather than a number that came out at zero.
set -euo pipefail
cd "$(dirname "$0")/.."

API="${ROVEQA_API_URL:-http://localhost:8000}"
OUT="${1:-smoke-archetypes.json}"
ACTIONS="${SMOKE_MAX_ACTIONS:-10}"
WAIT_SECONDS="${SMOKE_WAIT_SECONDS:-240}"

# label|origin|consent
SITES=(
  "minimal|https://example.com|leave"
  "institutional|https://www.iana.org|leave"
  "government-with-banner|https://www.gov.uk|reject"
  "machine-facing|https://httpbin.org|leave"
)

say() { printf '\n== %s\n' "$*" >&2; }
field() { python -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }
psql() { docker compose exec -T postgres psql -U agentic -d agentic_qa -tAc "$1" | tr -d '\r'; }

printf "[]" > "$OUT"

for entry in "${SITES[@]}"; do
  IFS='|' read -r label origin consent <<< "$entry"
  say "$label — $origin (consent: $consent)"

  project=$(curl -sS -X POST "$API/api/v1/projects" -H 'content-type: application/json' \
    -d "{\"name\":\"archetype $label\"}" | field project_id)
  curl -sS -X POST "$API/api/v1/projects/$project/run-policies" \
    -H 'content-type: application/json' \
    -d "{\"allowed_origins\":[\"$origin\"],\"max_duration_seconds\":200,
         \"max_actions\":$ACTIONS,\"max_model_calls\":0,\"destructive_actions\":false,
         \"consent\":\"$consent\",\"set_as_project_default\":true}" >/dev/null

  started=$(date +%s)
  run=$(curl -sS -X POST "$API/api/v1/runs" -H 'content-type: application/json' \
    -H "Idempotency-Key: arch-$project" \
    -d "{\"project_id\":\"$project\",\"explore\":true}" | field run_id)

  waited=0
  until [ "$waited" -ge "$WAIT_SECONDS" ]; do
    case "$(psql "select status from runs where run_id='$run'")" in
      completed|failed|cancelled) break ;;
    esac
    sleep 5
    waited=$((waited + 5))
  done
  elapsed=$(( $(date +%s) - started ))

  # Read back from the *public report*, not from the tables. If the answer a client gets
  # differs from what the database holds, the report is the one that matters — and that
  # gap is exactly the kind of thing a smoke should be able to catch.
  report=$(curl -sS "$API/api/v1/runs/$run/report")

  # Appended by a script file rather than a heredoc: `python - <<PY` reads the *script*
  # from stdin, so a pipe into it is swallowed and the first site died on an empty read.
  python scripts/_smoke_append.py "$OUT" "$label" "$origin" "$consent" "$run" "$elapsed"     <<< "$report"

done

python -m json.tool "$OUT" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
say "written to $OUT"
