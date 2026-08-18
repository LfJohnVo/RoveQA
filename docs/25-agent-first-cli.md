# Agent-First CLI Design

## Purpose
The React UI is for human control and observation. Coding agents and CI need a deterministic interface with stable contracts. `roveqa` is that interface.

## Boundary

```text
Claude Code / CI / shell
          |
        roveqa
          |
     HTTP / long-poll
          |
       FastAPI
          |
       Temporal
          |
       workers
```

The CLI is an Interface/Delivery adapter. It does not own QA decisions, browser state, workflows or persistence.

## Technology
Use TypeScript so the CLI can ship through npm/npx and reuse the existing pnpm toolchain and JSON schemas. Keep dependencies minimal and pin them after Phase 08 validation.

Suggested package layout:

```text
cli/
  src/
    commands/
    client/
    contracts/
    output/
    bundle/
  test/
  package.json
```

## Configuration
Precedence must be explicit and tested:

```text
command flag > environment variable > project config > user config > default
```

Never store secrets in project-tracked config. Project config may contain endpoint/project/environment identifiers only.

## Output contract
Text mode may be friendly. JSON mode is for agents:

```json
{
  "schema_version": "roveqa.cli.v1",
  "request_id": "...",
  "data": {}
}
```

Errors:

```json
{
  "schema_version": "roveqa.cli.v1",
  "request_id": "...",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "next_action": "...",
    "details": {}
  }
}
```

No progress line, warning, update notice or debug event may corrupt JSON stdout.

## TestPlan authoring
Plans use stable `step_id` values, plain-language intent and either an inline bounded budget or a referenced RunPolicy. `plan lint` must catch schema/budget/size problems offline before a run is submitted. Persisted plans keep `plan_id + plan_version`; a run records exactly which version executed.

## Request behavior
- Every request has a request ID.
- Every request has a bounded per-request timeout.
- Long-running `wait` uses repeated bounded long-polls but a separate total client deadline.
- Retry transport/503/429 only when safe and bounded.
- Never retry persistent 409 conflicts blindly.
- Never retry a side-effect trigger without the same idempotency key.
- Server `Retry-After` values must be capped by client policy.

## Run wait
`run wait` waits for a terminal verdict but does not own the run lifecycle.

```text
Ctrl-C / client timeout -> detach
explicit run cancel     -> cancel
```

A timeout result must include the `run_id`, last known status and a next action showing how to resume waiting.

## Failure bundle disk layout

```text
.roveqa/runs/<run-id>/failure/
  manifest.json
  result.json
  observation.json
  hypothesis.json          # optional, clearly model-derived
  steps.json
  console.jsonl
  network.jsonl
  screenshots/
  trace/
  video/
```

Materialize into a sibling temp directory first and promote files atomically. `manifest.json` is final. `.partial` means do not consume.

## Agent verification skill
The installed skill should enforce:

```text
feature/fix completed
  -> locate existing relevant plan
  -> run it; or author a minimal new plan
  -> wait for terminal verdict
  -> inspect evidence on failure
  -> never claim verified without a terminal result
```

For local development, target URLs are allowed when RunPolicy permits them; unlike hosted external testing products, RoveQA controls its local browser.

## Security
- Treat plan files as user input and validate size/schema.
- Treat downloaded/served artifact paths as identifiers, never arbitrary filesystem paths.
- Cap JSON response sizes/history accumulation.
- Redact secrets in logs and bundles.
- Never install/overwrite agent instruction files destructively; use a managed directory/section or explicit confirmation.
