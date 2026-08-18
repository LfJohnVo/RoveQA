# Phase 07 — User Story QA Workflow

## Objective
Convertir una historia + acceptance criteria en un **TestPlan versionado**, ejecución, verificación y findings trazables.

## Tasks
1. Executable User Story Contract schema.
2. Story Analyzer application service/model task.
3. Goal/acceptance criteria mapping.
4. Compilar el contrato/story a `contracts/test-plan.schema.json` sin perder relación `criterion_id -> plan step/assertion`.
5. Persist/export plan/version provenance para que el run nunca dependa sólo de "current plan" mutable.
6. Deterministic + semantic verifier pipeline.
7. Clasificación de non-pass: `product`, `plan`, `environment`, `policy`, `agent_budget`, `model`, `unknown/inconclusive`.
8. Finding creation con evidence refs/evidence_set identity.
9. Report generator Markdown/JSON que separe `deterministic_observation` de `root_cause_hypothesis`/recommendation generada por modelo.
10. End-to-end demo contra test-target-app.
11. Plan-quality fixtures: assertion ambigua/presence-only/branching excesivo no deben reportarse automáticamente como product defect.

## Gates
- Una story conocida pasa/falla de forma reproducible.
- El TestPlan resultante valida contra su schema y puede exportarse/importarse losslessly.
- Cada failed criterion apunta a evidence/action timeline del mismo run/evidence set.
- Report no depende de transcript completo del LLM.
- Un plan malo conocido puede terminar `blocked/inconclusive` con failure kind de plan/budget en vez de culpar incorrectamente al producto.

## Required skills
- `prompt-engineering-patterns`
- `api-design-principles` when exposing story/plan/run contracts
- `error-handling-patterns`
- `durability-review`
