# Phase 08 — Agent-First CLI and Verification Contracts

## Objective
Expose the self-hosted platform through a thin, deterministic CLI that coding agents and CI can drive without scraping the React UI. The CLI must call the FastAPI control plane; it must not re-implement Temporal, LangGraph, Playwright, model routing, persistence or QA logic.

## Architectural decision
- Implementation: TypeScript CLI package using the existing pnpm/TypeScript toolchain.
- Runtime role: Interface/Delivery adapter over REST/long-poll APIs.
- Source of truth: backend contracts and JSON schemas in `contracts/`.
- Browser/model execution remains exclusively server/worker-side.
- `--output json` stdout is machine-pure; diagnostics/progress go to stderr.

## Required commands v1
1. `roveqa setup` — create/update local CLI config only; no hidden cloud dependency.
2. `roveqa doctor` — CLI version, API reachability, server readiness, contract/version compatibility.
3. `roveqa project list|get`.
4. `roveqa plan scaffold|lint` — fully local, no credentials, no browser/model calls.
5. `roveqa run create --plan <file>` — submit a versioned TestPlan with an auto-generated or explicit idempotency key.
6. `roveqa run get <run-id>`.
7. `roveqa run wait <run-id> [--timeout]` — bounded long-poll with a total client deadline; timeout detaches, never cancels implicitly.
8. `roveqa run cancel <run-id>` — explicit cancellation.
9. `roveqa run rerun <run-id|plan-id>` — new durable run preserving provenance.
10. `roveqa run diff <run-a> <run-b>` — deterministic verdict/step/fingerprint deltas before any semantic summary.
11. `roveqa run artifact <run-id> --out <dir>`.
12. `roveqa run failure <run-id> --out <dir>` — materialize one self-consistent FailureBundle.
13. `roveqa run flaky <plan-id|plan-file> --count N` — replay with documented memory/model policy and calculate stability.
14. `roveqa agent install claude` — install a project verification skill that drives this local/self-hosted CLI after application changes.

## Contracts
Implement and validate:
- `contracts/test-plan.schema.json`
- `contracts/failure-bundle.schema.json`
- `contracts/cli-envelope.schema.json`
- documented stable exit-code mapping
- `X-Request-Id` propagation
- `Idempotency-Key` for mutation triggers
- version/ETag or equivalent optimistic concurrency for mutable plan definitions when persisted

## Result semantics
Terminal verdicts are domain values and must not be inferred from process success:
- `passed`
- `failed`
- `blocked`
- `inconclusive`
- `cancelled`

CLI exit code families:
- `0`: successful command / terminal `passed`
- `1`: terminal non-pass verdict (`failed|blocked|inconclusive|cancelled`)
- `2`: usage/configuration
- `3`: authentication/authorization
- `4`: not found
- `5`: validation/contract error
- `6`: conflict/version mismatch
- `7`: client wait timeout; run may still be active
- `8`: transport/service unavailable
- `9`: internal/unclassified
- `10`: policy denied
- `11`: rate limited/resource unavailable

JSON output must still carry the precise typed `error.code` or `verdict` so agents do not rely only on the numeric exit code.

## FailureBundle invariants
- Every member references the same `run_id`, `evidence_set_id`, target version/fingerprint context and plan version.
- Never combine "latest screenshot" with a different run's DOM/console/network trace.
- Write bundle files to a temporary directory first.
- Write/rename `manifest.json` last; its presence means the bundle is complete.
- Leave a `.partial` marker on failed materialization.
- Keep deterministic observations separate from LLM `root_cause_hypothesis` and `recommended_fix_target`.

## Plan-authoring rules
- Plans describe user intent, not CSS/XPath selectors.
- Prefer one user action per step.
- Assertions must verify working outcomes, not only element presence.
- Layout-sensitive requirements must name geometry/relationship expectations.
- Every plan has stable `step_id` values for evidence/diff provenance.
- Every plan has a bounded action/time/model-call policy or references a RunPolicy.
- Plans are version-control friendly and importable/exportable without information loss.

## Tests
1. CLI subprocess contract tests for stdout/stderr purity and exit codes.
2. JSON-schema contract tests using backend + CLI fixtures.
3. Idempotency replay test: retrying a trigger with the same key returns the same logical run/result rather than duplicating side effects.
4. Wait timeout test: exit 7 with `run_id` and resumable next action; server run continues.
5. Ctrl-C/detach test: interrupting `run wait` does not cancel the run.
6. FailureBundle cross-run contamination tests.
7. Atomic bundle materialization and `.partial` test.
8. Dry-run/scaffold/lint tests requiring neither API nor model/browser.
9. Stable-step/provenance test: plan edits preserve explicit step identity rules and run evidence references the executed plan version.
10. Compatibility test between CLI and API contract versions.
11. Agent-install test in a temporary repository without clobbering existing Claude instructions.

## Gates
- A coding agent can `plan lint -> run create -> run wait -> run failure -> rerun` using only stable machine-readable output.
- No CLI command directly invokes Playwright, vLLM, AirLLM, PostgreSQL, Redis or Temporal SDK.
- Killing the CLI during `run wait` leaves the server-side run intact and recoverable.
- Duplicate trigger retries cannot create duplicate target side effects merely because the client lost the first response.
- FailureBundle integrity tests reject mixed run/evidence identities.
- `--output json` emits exactly one parseable JSON value to stdout on every supported success/error path.
- Plans and failure bundles round-trip through their schemas.

## Required skills
- `api-design-principles`
- `error-handling-patterns`
- `systematic-debugging` for unexpected contract failures
- `durability-review`
- `ponytail`
