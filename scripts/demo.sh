#!/usr/bin/env bash
# The demo: two runs against the bundled application, seen the way a client sees them.
#
#   ./scripts/demo.sh
#
# One story that the application satisfies and one that it cannot, because a QA tool
# that only ever reports success is indistinguishable from one that is broken. The
# second run is the interesting one: it produces evidence, and the bundle that carries
# that evidence is materialized and checked against its own manifest.
#
# Everything after the setup goes through the CLI — the same binary an external client
# installs — so what this prints is what a coding agent would read.
#
# Requires the stack up (`docker compose up -d`) and a model endpoint for the worker.
set -euo pipefail
cd "$(dirname "$0")/.."

API="${ROVEQA_API_URL:-http://localhost:8000}"
TARGET="${DEMO_TARGET_ORIGIN:-http://frontend:5173}"
CLI="${ROVEQA_CLI:-node cli/dist/main.js}"
WAIT="${DEMO_WAIT:-10m}"
OUT="${DEMO_OUT_DIR:-demo-out}"

say() { printf '\n== %s\n' "$*"; }
field() { python -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }
# The CLI answers with an envelope and the payload lives under `data`. Reading both it
# and a plain API response with the same helper is how this script first came back with
# an empty run id and a validation error instead of a run.
envelope() { python -c "import sys,json;print((json.load(sys.stdin).get('data') or {}).get('$1',''))"; }

rm -rf "$OUT" && mkdir -p "$OUT"

say "a project and a policy that fences the run to $TARGET"
PROJECT=$(curl -sS -X POST "$API/api/v1/projects" -H 'content-type: application/json' \
  -d '{"name":"RoveQA demo"}' | field project_id)
# `destructive_actions` is deny-by-default, and it covers every action that can change
# the application — clicking included. A policy without it lets the agent look and never
# touch, which is the right default and the wrong setting for a demo that has to act.
curl -sS -X POST "$API/api/v1/projects/$PROJECT/run-policies" -H 'content-type: application/json' \
  -d "{\"allowed_origins\":[\"$TARGET\"],\"max_duration_seconds\":240,\"max_actions\":12,
       \"max_model_calls\":12,\"destructive_actions\":true,
       \"set_as_project_default\":true}" >/dev/null
echo "project $PROJECT"

POLICY=$(docker compose exec -T postgres psql -U agentic -d agentic_qa -tAc \
  "select policy_id from run_policies where project_id='$PROJECT'" | tr -d ' \r')

# Two stories. The hint is what the deterministic check looks for on the page: the
# first is there, the second is not and cannot be — no model opinion decides either.
# The plan is compiled from its story and then exported to a file, because a plan file
# is what a client actually holds. The exported document keeps `source_story_id`, so
# the criteria and their hints travel with it.
plan_file() {  # $1 = goal, $2 = criterion id, $3 = hint, $4 = destination file
  local story plan plan_id plan_version
  story=$(curl -sS -X POST "$API/api/v1/projects/$PROJECT/stories" \
    -H 'content-type: application/json' \
    -d "{\"actor\":\"a QA engineer\",\"goal\":\"$1\",
         \"acceptance_criteria\":[{\"criterion_id\":\"$2\",
           \"description\":\"$1\",\"verification_hint\":\"$3\"}]}" | field story_id)
  plan=$(curl -sS -X POST "$API/api/v1/stories/$story/plans" \
    -H 'content-type: application/json' -d "{\"run_policy_id\":\"$POLICY\"}")
  plan_id=$(printf '%s' "$plan" | field plan_id)
  plan_version=$(printf '%s' "$plan" | field plan_version)
  curl -sS "$API/api/v1/plans/$plan_id/versions/$plan_version" -o "$4"
  # Validated against the published schema before anything is executed.
  $CLI plan lint "$4" --output json >/dev/null
}

plan_file "open the application" "ac-loaded" "RoveQA" "$OUT/pass.plan.json"
plan_file "find the confirmed order" "ac-order" "Order #4711" "$OUT/fail.plan.json"

run_and_wait() {  # $1 = plan file, $2 = label -> prints the run id
  # The key carries the project, because a stable key is a promise that the same key
  # means the same request. Running the demo twice with a bare "demo-pass" earns a 409
  # — the server refusing to pretend two different runs are one retry.
  local run code
  run=$($CLI run create --plan "$1" --project "$PROJECT" --api-url "$API" \
    --idempotency-key "demo-$PROJECT-$2" --output json | envelope run_id)
  echo "$2: run $run" >&2
  # `run wait` exits 0 on pass, 1 on any other terminal verdict, 7 if the client's own
  # deadline expires with the run still alive. 7 is not a verdict and the demo must not
  # report it as one.
  set +e
  $CLI run wait "$run" --timeout "$WAIT" --api-url "$API" --output json >"$OUT/$2.json"
  code=$?
  set -e
  echo "$2: exit $code, verdict $(envelope verdict <"$OUT/$2.json")" >&2
  if [ "$code" -eq 7 ]; then
    echo "$2: the wait timed out with the run still running — not a verdict" >&2
  fi
  printf '%s' "$run"
}

say "run 1 — a story the application satisfies"
run_and_wait "$OUT/pass.plan.json" pass >/dev/null

say "run 2 — a story it cannot"
FAILED_RUN=$(run_and_wait "$OUT/fail.plan.json" fail)

say "the evidence for run 2"
# `run failure` refuses a bundle whose bytes do not hash to what the manifest declares,
# so reaching this line is the integrity check passing, not a claim that it did. The
# re-hash below is for the reader, and would catch a bundle edited after the fact.
if $CLI run failure "$FAILED_RUN" --out "$OUT/bundle" --api-url "$API" --output json \
     >"$OUT/bundle.json"; then
  echo "bundle at $OUT/bundle"
  python - "$OUT/bundle/manifest.json" <<'PY'
import hashlib, json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
root = pathlib.Path(sys.argv[1]).parent
print(f"  manifest {manifest['schema_version']}  run {manifest['run_id']}")
print(f"  verdict {manifest['verdict']}  observation: {manifest.get('deterministic_observation')}")
for artifact in manifest["artifacts"]:
    body = (root / artifact["relative_path"]).read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    ok = "ok" if digest == artifact["sha256"] and len(body) == artifact["size_bytes"] else "MISMATCH"
    print(f"  {artifact['relative_path']}  {len(body)} bytes  {ok}")
PY
else
  echo "no bundle: run 2 did not reach a failing verdict with evidence" >&2
fi

say "done"
echo "project $PROJECT   output in $OUT/"
