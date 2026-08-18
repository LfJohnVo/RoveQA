# TestSprite CLI Evaluation and Adopted Patterns

## Decision summary

`TestSprite/testsprite-cli` is **not** a replacement for the RoveQA runtime architecture. It is useful as a reference implementation for an agent-first testing interface and reliability contracts.

The reviewed repository explicitly defines itself as a thin client to TestSprite's hosted API. Browser automation, plan generation and test execution are server-side platform behavior, and running tests requires a TestSprite account/API key. That is incompatible with the primary RoveQA goals: self-hosted execution, local Playwright control, local vLLM/AirLLM inference, durable Temporal/LangGraph state and a first-party knowledge graph.

Therefore:

- Do **not** add TestSprite CLI as a runtime dependency.
- Do **not** replace Playwright/LangGraph/Temporal with TestSprite.
- Do **not** couple core product behavior to a TestSprite account or hosted API.
- Do adopt the strongest agent-facing contracts and operational patterns in an original implementation.
- Do not fork the CLI as RoveQA's foundation: its published scope intentionally excludes the engine we need, and its canonical development is described as internal/mirrored rather than this repository being the whole platform source.

## Viability comparison

| Requirement | RoveQA architecture | TestSprite CLI repo | Decision |
|---|---|---|---|
| Self-hosted browser execution | Yes | No; hosted platform executes tests | Keep RoveQA |
| Local vLLM/AirLLM | Yes | Not implemented by CLI | Keep RoveQA |
| Long-running durable workflows | Temporal + checkpoints | CLI polls remote run | Keep Temporal |
| Local learned knowledge graph | Graphiti/FalkorDB | Not a CLI responsibility | Keep RoveQA |
| Full browser/runtime implementation available OSS | Planned in repo | No; CLI only | Keep RoveQA |
| Agent-friendly machine interface | Planned | Strong | Adopt patterns |
| Stable JSON + exit codes | Must add | Strong | Adopt |
| Versioned declarative test plan | Must add | Strong | Adopt/improve |
| Atomic failure evidence bundle | Must add | Strong | Adopt/improve |
| Idempotent run triggers | Required | Strong | Adopt |
| Dry-run/lint/scaffold | Useful | Strong | Adopt |
| Flakiness/replay/diff workflows | Useful | Strong | Adopt |
| Agent skill installation | Useful | Strong | Adopt |
| Tests as files/version control | Desired | Partial/open area upstream | Make first-class in RoveQA |

## Patterns adopted

### 1. Agent-first CLI
Add a thin `roveqa` CLI that treats FastAPI as its only product boundary. It never imports Temporal SDK, LangGraph, Playwright, Redis, PostgreSQL or model libraries.

Primary verification loop:

```text
plan scaffold/lint
        ->
run create
        ->
run wait
        ->
if failed: run failure
        ->
fix / inspect
        ->
run rerun
```

### 2. Machine-pure output
`--output json` emits one parseable JSON value to stdout. Progress, warnings and debug output go to stderr. Exit codes are a stable public contract.

### 3. Versioned TestPlan files
Plans are normal files suitable for Git review and backup. They use JSON Schema and describe user intent rather than browser selectors.

RoveQA improves the idea by making plan definition round-trip a v1 requirement instead of treating authored frontend plans as server-only state.

### 4. Atomic FailureBundle
A failure bundle must be self-consistent. Every artifact must belong to the same run/evidence identity and target/plan version. The bundle is finalized atomically by writing `manifest.json` last; failed writes retain a `.partial` marker.

### 5. Idempotency and retry ownership
Every mutation trigger gets an `Idempotency-Key` or a naturally-idempotent contract. Retry policy distinguishes transient transport/unavailable errors from persistent conflicts. Exactly one layer owns a given retry/rate-limit loop to avoid multiplicative retries.

### 6. Wait does not mean cancel
A CLI wait timeout or Ctrl-C detaches the client. The durable server-side run remains active unless an explicit cancel command is sent.

### 7. Runtime response validation
CLI responses are validated at runtime against versioned schemas. Agents must never receive a success exit with a malformed partial response merely because TypeScript static types said a field existed.

### 8. Plan-quality classification
A non-pass result is classified before blaming the product. RoveQA must distinguish at least:

- product defect
- test/plan ambiguity
- environment/infra
- policy block
- model/agent budget exhaustion
- unknown/inconclusive

This classification must cite deterministic evidence where available and keep LLM hypotheses explicitly separate.

### 9. Flakiness and run diff
Provide deterministic run-to-run comparison and repeated-run stability scores. This is especially valuable for an agentic tester where model variance can masquerade as product variance.

### 10. Agent installation
`roveqa agent install claude` installs a verification workflow in a target repository. It must preserve existing project instructions and should only activate once a RoveQA endpoint/project is configured.

## Patterns deliberately not copied

- Hosted TestSprite API dependency.
- Credit/billing model.
- Restriction that the CLI cannot test localhost.
- Server-owned opaque browser implementation.
- Any code copied verbatim from the TestSprite repository.

RoveQA may test localhost/private environments because it owns the browser runtime. Network access remains constrained by explicit `RunPolicy` allowlists.

## Risks learned from upstream issues

The TestSprite issue tracker also provides useful warnings for our implementation:

- verbose/branching assertions can exhaust agent budgets and produce false `blocked` results;
- unbounded histories/steps can become memory hazards;
- file-reading flags need path/size/secret guards;
- static types without runtime validation can yield malformed success output;
- agent skill installation can drift when every agent format is bespoke.

RoveQA therefore requires bounded plans/history reads, runtime schemas, guarded file inputs, explicit budget failure kinds and a canonical skill template.

## Optional external benchmark

TestSprite may still be useful as a **non-required external oracle/benchmark** during development when a contributor has an account and a reachable test environment. A benchmark adapter may compare the same high-level scenario across RoveQA and an external system, but:

- it lives in test/tooling scope, not runtime core;
- CI must have a fully local path that does not require it;
- no RoveQA verdict is delegated to TestSprite as authoritative truth;
- credentials are opt-in and never committed;
- benchmark results are tagged with provider/version/date because agentic behavior can change.

This can help evaluate plan quality, success rate and evidence ergonomics without sacrificing self-hosted operation.

## License note

The reviewed repository is Apache-2.0. This blueprint adopts design patterns and public-interface lessons only; it does not vendor or copy TestSprite source. If future implementation copies or derives source code, perform a dedicated license/NOTICE review before merging.
