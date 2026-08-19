# roveqa CLI

The agent-first interface to a self-hosted RoveQA. It is an Interface/Delivery
adapter over the FastAPI control plane: it never touches Playwright, Temporal,
LangGraph, PostgreSQL, Redis or a model directly.

## Contract

`--output json` writes **exactly one** JSON value to stdout and nothing else.
Progress, warnings and debug go to stderr, so `roveqa ... --output json > result.json`
always yields a parseable file.

```json
{ "schema_version": "roveqa.cli.v1", "request_id": "…", "data": {} }
{ "schema_version": "roveqa.cli.v1", "request_id": "…", "error": { "code": "…", "message": "…" } }
```

Exit codes are part of the contract: `0` success or a passing verdict, `1` a terminal
non-pass verdict, `2` usage/config, `4` not found, `5` validation, `6` conflict,
`7` wait timeout (the run continues), `8` transport, `10` policy denied.

`7` matters most: a timeout is the absence of an answer, not a failing one.

## Configuration

    command flag > environment variable > project config > user config > default

Project config (`.roveqa/config.json`, version-controlled) may carry endpoints and
identifiers only. A token there is refused; use `ROVEQA_TOKEN` or the user config.

## Commands

```bash
roveqa doctor --output json
roveqa plan scaffold --project <id> --policy-id <id> > plan.json
roveqa plan lint plan.json
roveqa run create --plan plan.json --output json
roveqa run wait <run-id> --timeout 300000 --output json
roveqa run cancel <run-id>
```

`plan scaffold` and `plan lint` are entirely local: no API, no credentials, no model.

Waiting is not owning. `run wait` detaches on Ctrl-C or on its own deadline and the
run keeps going; stopping a run takes an explicit `run cancel`.
