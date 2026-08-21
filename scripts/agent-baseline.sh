#!/usr/bin/env bash
# What the agent can actually verify, measured rather than remembered.
#
#   bash scripts/agent-baseline.sh            # one pass
#   BASELINE_REPEATS=3 bash scripts/agent-baseline.sh
#
# Four story shapes, each of which failed for a different reason before Phase 15:
#
#   one-page      a text criterion on the first page. The minimum, and it was impossible
#   multi-page    a criterion on the way and another at the end. The ordinary shape for a
#                 landing page or a shop, and inexpressible: criteria were judged against
#                 the page the run stopped on
#   after-a-form  a criterion visible only after typing and submitting
#   unreachable   a goal the application has no path to. It must come back `blocked` with
#                 a cause and never `failed`, because `failed` accuses the product
#
# The first three run under a **read-only** policy, which is both the safe default and
# the mode that used to die on its first navigation. Only `after-a-form` gets permission
# to write.
#
# Output is a single JSON object on stdout; progress goes to stderr. Redirect and diff it
# against the last one — that is the whole point of a baseline.
#
# Two metrics the Phase 15 plan asked for are *not* here, and the omission is deliberate
# rather than forgotten: model calls per verified criterion, and the `invalid_action` rate.
# Neither is exposed by the public API - `RunResponse` carries no counters and the report
# carries no inference metrics - and this script speaks only to that API, on purpose. The
# numbers exist in the worker's logs, where they are not a contract.
#
# Getting them properly means adding run counters to the report, which is a public contract
# change and belongs in a slice of its own. Said here so a reader is not left to infer that
# the agent makes no model calls.
#
# Requires: the stack up, and a model endpoint for the worker. Without one this reports
# `model: absent` and exits 3 rather than printing zeros that look like a result.
set -euo pipefail
cd "$(dirname "$0")/.."

API="${ROVEQA_API_URL:-http://localhost:8000}"
TARGET="${BASELINE_TARGET_ORIGIN:-http://target-app:8000}"
REPEATS="${BASELINE_REPEATS:-1}"
WAIT_SECONDS="${BASELINE_WAIT_SECONDS:-420}"

say() { printf '== %s\n' "$*" >&2; }
jfield() { python -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }

# --------------------------------------------------------------------------------------
# Refuse to produce a number that means nothing.
# --------------------------------------------------------------------------------------
say "checking the stack"
curl -sS -fm 10 "$API/health" >/dev/null || {
  echo "the API at $API is not answering; start the stack first" >&2
  exit 8
}

model="$(docker compose exec -T worker sh -c 'echo "$VLLM_BASE_URL"' 2>/dev/null | tr -d '\r')"
if [ -z "$model" ]; then
  # Said plainly rather than measured anyway. A suite that needs a GPU and does not say so
  # reports a flat zero, which reads like a regression instead of a missing dependency.
  printf '{"model":"absent","note":"no VLLM_BASE_URL on the worker; every run would come back inconclusive"}\n'
  echo "no model endpoint configured on the worker — nothing to measure" >&2
  exit 3
fi

say "target: $TARGET"
say "model endpoint: $model"

say "starting the bundled target application"
docker compose --profile baseline up -d --wait target-app >/dev/null 2>&1 || {
  echo "could not start target-app" >&2
  exit 8
}

PROJECT="$(curl -sS -X POST "$API/api/v1/projects" -H 'content-type: application/json' \
  -d '{"name":"agent baseline"}' | jfield project_id)"
say "project $PROJECT"

policy() {  # $1 = destructive
  curl -sS -X POST "$API/api/v1/projects/$PROJECT/run-policies" \
    -H 'content-type: application/json' \
    -d "{\"allowed_origins\":[\"$TARGET\"],\"max_duration_seconds\":300,
         \"max_actions\":25,\"max_model_calls\":25,\"destructive_actions\":$1}" | jfield policy_id
}

READ_ONLY="$(policy false)"
INTERACTIVE="$(policy true)"

# --------------------------------------------------------------------------------------
# The four shapes. Literals are the ones the fixture really renders; a criterion whose
# text is guessed produces a false accusation, which is the one failure that matters.
# --------------------------------------------------------------------------------------
story() {  # $1 = json file
  curl -sS -X POST "$API/api/v1/projects/$PROJECT/stories" \
    -H 'content-type: application/json' --data-binary "@$1" | jfield story_id
}

plan_for() {  # $1 = story id
  curl -sS -X POST "$API/api/v1/stories/$1/plans" -H 'content-type: application/json' \
    -d '{"max_actions":20,"max_duration_seconds":280,"max_model_calls":20}' | jfield plan_id
}

# A path under the repository rather than `mktemp -d`: this script is bash and the
# summary below is python, and on a Windows host those two do not agree about what
# `/tmp` is. A relative path means the same thing to both.
workdir=".agent-baseline"
rm -rf "$workdir" && mkdir -p "$workdir"

cat > "$workdir/one-page.json" <<'JSON'
{"actor": "a visitor",
 "goal": "open the home page of the application",
 "acceptance_criteria": [
   {"criterion_id": "ac-home", "description": "the home page names itself",
    "verification_hint": "Home"},
   {"criterion_id": "ac-ready", "description": "the home page reports it is ready",
    "verification_hint": "ready"}]}
JSON

cat > "$workdir/multi-page.json" <<'JSON'
{"actor": "a visitor",
 "goal": "start on the home page and then open the records page",
 "acceptance_criteria": [
   {"criterion_id": "ac-came-from-home", "description": "the run passed through the home page",
    "verification_hint": "ready"},
   {"criterion_id": "ac-reached-records", "description": "the records page offers to create one",
    "verification_hint": "Create record"}]}
JSON

# Written per attempt, further down, because the reference has to be unique: the fixture
# refuses a duplicate and answers "already exists", so a fixed reference passes on the
# first run of the day and never again. A real QA run does not assume a clean database
# either, so unique data is the honest shape rather than a workaround.
write_after_a_form() {  # $1 = unique reference
  cat > "$workdir/after-a-form.json" <<JSON
{"actor": "an operator",
 "goal": "on the records page, create a record with reference $1 and name Probe",
 "acceptance_criteria": [
   {"criterion_id": "ac-created", "description": "the application confirms the record was created",
    "verification_hint": "Created $1"}]}
JSON
}
write_after_a_form "BASELINE-seed"

cat > "$workdir/unreachable.json" <<'JSON'
{"actor": "an analyst",
 "goal": "open the quarterly revenue forecast, which this application does not have",
 "acceptance_criteria": [
   {"criterion_id": "ac-forecast", "description": "the forecast is shown",
    "verification_hint": "Quarterly revenue forecast"}]}
JSON

declare -A POLICY=(
  [one-page]="$READ_ONLY"
  [multi-page]="$READ_ONLY"
  [after-a-form]="$INTERACTIVE"
  [unreachable]="$READ_ONLY"
)
SHAPES=(one-page multi-page after-a-form unreachable)

# --------------------------------------------------------------------------------------
# Run them.
# --------------------------------------------------------------------------------------
results="$workdir/results.jsonl"
: > "$results"

for shape in "${SHAPES[@]}"; do
  # One story per shape, except the one whose data must not repeat.
  if [ "$shape" != "after-a-form" ]; then
    sid="$(story "$workdir/$shape.json")"
    pid="$(plan_for "$sid")"
  fi
  for attempt in $(seq 1 "$REPEATS"); do
    say "$shape, attempt $attempt"
    started="$(date +%s)"
    if [ "$shape" = "after-a-form" ]; then
      write_after_a_form "BASELINE-$started-$attempt"
      sid="$(story "$workdir/$shape.json")"
      pid="$(plan_for "$sid")"
    fi
    run="$(curl -sS -X POST "$API/api/v1/runs" -H 'content-type: application/json' \
      -H "Idempotency-Key: baseline-$shape-$attempt-$started" \
      -d "{\"project_id\":\"$PROJECT\",\"plan_id\":\"$pid\",\"plan_version\":\"1\",
           \"run_policy_id\":\"${POLICY[$shape]}\"}" | jfield run_id)"

    deadline=$(( started + WAIT_SECONDS ))
    status=running
    terminal=false
    while [ "$(date +%s)" -lt "$deadline" ]; do
      status="$(curl -sS "$API/api/v1/runs/$run" | jfield status)"
      case "$status" in completed|failed|cancelled) terminal=true; break;; esac
      sleep 5
    done
    elapsed=$(( $(date +%s) - started ))

    # A run still going when the wait expired is not a result. Recording its report anyway
    # would put a half-finished verdict in the baseline and make the next diff meaningless
    # -- and it is exactly the mistake the CLI's exit-code contract exists to prevent:
    # waiting is not owning, and a timeout says nothing about the run.
    if [ "$terminal" != true ]; then
      say "$shape attempt $attempt did not finish within ${WAIT_SECONDS}s; recorded as such"
      printf '%s
' "{\"shape\":\"$shape\",\"attempt\":$attempt,\"run_id\":\"$run\",
        \"status\":\"$status\",\"verdict\":null,\"criteria_total\":0,\"criteria_met\":0,
        \"failure_kinds\":[],\"seconds\":$elapsed,\"timed_out\":true}"         | tr -d '
' >> "$results"
      printf '
' >> "$results"
      continue
    fi

    curl -sS "$API/api/v1/runs/$run/report" | python -c "
import json, sys
report = json.load(sys.stdin)
criteria = report.get('criteria', [])
print(json.dumps({
    'shape': '$shape',
    'attempt': $attempt,
    'run_id': '$run',
    'status': '$status',
    'verdict': report.get('verdict'),
    'criteria_total': len(criteria),
    'criteria_met': sum(1 for c in criteria if c.get('outcome') == 'met'),
    'failure_kinds': sorted({c['failure_kind'] for c in criteria if c.get('failure_kind')}),
    'seconds': $elapsed,
}))" >> "$results"
  done
done

# --------------------------------------------------------------------------------------
# One JSON value on stdout. Machine-pure, like the CLI's own contract.
# --------------------------------------------------------------------------------------
python -c "
import json, sys

runs = [json.loads(line) for line in open('$results') if line.strip()]
by_shape = {}
for run in runs:
    by_shape.setdefault(run['shape'], []).append(run)

def summarise(rows):
    return {
        'runs': len(rows),
        'timed_out': sum(1 for r in rows if r.get('timed_out')),
        'verdicts': {v: sum(1 for r in rows if r['verdict'] == v)
                     for v in sorted({r['verdict'] for r in rows if r['verdict']})},
        'criteria_met': sum(r['criteria_met'] for r in rows),
        'criteria_total': sum(r['criteria_total'] for r in rows),
        'failure_kinds': sorted({k for r in rows for k in r['failure_kinds']}),
        'median_seconds': sorted(r['seconds'] for r in rows)[len(rows) // 2],
    }

# The property the phase is judged on, stated so a diff shows it moving.
reachable = [r for r in runs if r['shape'] != 'unreachable']
unreachable = [r for r in runs if r['shape'] == 'unreachable']
print(json.dumps({
    'model': 'present',
    'target': '$TARGET',
    'repeats': $REPEATS,
    'by_shape': {shape: summarise(rows) for shape, rows in sorted(by_shape.items())},
    'headline': {
        'reachable_passed': sum(1 for r in reachable if r['verdict'] == 'passed'),
        'reachable_runs': len(reachable),
        'unreachable_never_failed': all(r['verdict'] != 'failed' for r in unreachable),
        # A pass rate computed over runs that never finished is not a pass rate.
        'timed_out': sum(1 for r in runs if r.get('timed_out')),
    },
    'runs': runs,
}, indent=2))
"

say "done"
