# Memory Evaluation — reach the records page

Instantiates `templates/MEMORY_EVAL_TEMPLATE.md` for the Phase 09 gate.

Two measurements, kept separate because they answer different questions and only one
of them is about a model:

| | Harness | Reproduced by |
| --- | --- | --- |
| **A. Mechanism** | planner double that reacts to memory | `backend/tests/knowledge/test_memory_benchmark.py` (every gate run) |
| **B. Real model** | Qwen3-4B on the RTX 5060 Ti, real Chromium, real target app | `backend/tests/knowledge/test_memory_benchmark_real_model.py` (skipped without `VLLM_BASE_URL`) |

## Scope
- Project/environment: a disposable project per run, environment `staging`
- TestPlan/version: one deterministic criterion (`ac-create-record`) in A; a goal
  phrased as an outcome in B
- App version/fingerprint: `2.1.0`, origin the ephemeral target-app URL
- Model configuration (B): `Qwen/Qwen3-4B-Instruct-2507` on vLLM `v0.27.1-cu129`,
  `max_model_len` 16384, structured outputs on
- Date: 2026-08-19

## A. Mechanism — cold baseline vs warm run

| | Cold | Warm |
| --- | --- | --- |
| Planner calls | 5 | **2** |
| Browser actions | 4 | **1** |
| Retrieved memory items | 0 | 2 |
| Verdict | `passed` | `passed` |

Reduction: **60%** planner calls, **75%** browser actions.

Runs through the real pipeline — durable consolidation, the real retrieval query, the
real promotion gates, the real `MemoryContext` — with a planner double that probes
candidate routes when it knows nothing and goes straight to a remembered route when
memory names one.

## B. Real model — cold baseline vs warm run

| | Cold | Warm |
| --- | --- | --- |
| Planner calls | 4 | **2** |
| Browser actions | 3 | **1** |
| Actions taken | navigate, navigate, check | navigate |
| Ended at | `/records` | `/records` |

Reduction: **50%** planner calls, **67%** browser actions.

The goal is phrased as an outcome ("confirm the records page is open and shows its
create-record form"), never as a path — naming `/records` in the goal would have let
the cold run navigate straight there and the benchmark would be measuring the wording.
Memory supplies one promoted, observed `route`. The model reads it in the
`<recalled_memory>` block and goes directly, instead of walking the home page first.

## Quality
- Same acceptance criteria result? **yes.** Both runs in A pass; both runs in B end at
  the same URL, asserted from the episode's observed URL rather than from what the
  model said it was doing
- Evidence quality equivalent/better? equivalent — the warm run captures the same
  criterion result against the same page
- Any stale/incorrect memory used? no. Memory recorded under app version `2.1.0`
  arrives as `revalidate` on `3.0.0` and is *checked* rather than followed
- Any policy/safety bypass? no. Memory reaches the planner as labelled text; every
  action it proposes still passes the RunPolicy guard unchanged from Phase 04. The
  benchmark's own policy allows side effects because this model escalates its
  navigations — a read-only policy would have denied the first step of *both* runs and
  the measurement would have been about the policy

## Delta
- Model call reduction: **60%** (mechanism) / **50%** (real model)
- Browser action reduction: **75%** (mechanism) / **67%** (real model)
- Decision latency reduction: not measured. Wall-clock here is dominated by browser
  startup, which both runs pay equally

## Decision
**PROMOTE.**

The gate asks for ≥20% on one primary metric without degrading a correct verdict. Both
harnesses clear it on both metrics, and the real-model run is the one that matters:
given a remembered route, Qwen3-4B stops exploring and goes there.

## Notes / provenance
- **A defect this benchmark found, now fixed.** The real model proposed a `check` whose
  target had no role, label or text. The Playwright adapter raised, the exception
  escaped the agent graph, and the episode died — so Temporal would have retried the
  whole episode and the planner would have proposed the same unusable action again
  (the failure mode ADR 0009 exists to prevent). Now typed as
  `UnperformableActionError`, recorded as a failed step, and covered by a regression
  test in `tests/agent/test_graph.py`.
- **Remaining bottleneck: no embedding endpoint by default.** Retrieval ranks
  deterministically over a text-matched pool. Semantic recall is the part most likely
  to matter on flows where the goal wording and the remembered summary differ; this
  measurement does not exercise it.
- **Not measured:** how the numbers move on a large graph, or with dozens of competing
  memory items. Both benchmarks use a small, clean scope.
- First run is never warm, asserted rather than assumed: promotion needs two
  independent agreeing runs, so a baseline cannot accidentally measure a warm run.
- The threshold lives in both tests as `MIN_REDUCTION`, so this document cannot drift
  away from what the suite enforces.
