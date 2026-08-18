# Definition of Done

Un feature/slice está Done cuando:
- Acceptance criteria demostrables.
- Tests apropiados verdes.
- Lint/type-check verdes.
- Boundaries arquitectónicos respetados.
- Error/retry/idempotency behavior definido cuando aplica.
- Telemetría mínima para diagnosticarlo.
- Docs/contract actualizados si aplica.
- No secrets ni datos sensibles en commits/logs de test.
- Todo cambio a contrato público (`TestPlan`, API, events, CLI envelope, FailureBundle) está versionado/validado y tiene contract tests.
- Evidencia determinista no se mezcla semánticamente con hipótesis LLM.

Para features verificables por RoveQA después de Phase 08:
- existe al menos un plan relevante reutilizado o creado de forma versionable;
- se obtuvo un verdict terminal real cuando el entorno de test estaba disponible;
- no se declara "verified" basándose sólo en unit tests o en una ejecución que todavía está running/timeout;
- si no se pudo realizar el E2E, el estado queda explícitamente `unverified`, no maquillado como PASS.

Una fase está Done cuando además:
- Todos los gates de su plan se ejecutaron.
- `PROGRESS.md` actualizado.
- `HANDOFF.md` permite continuar en una sesión nueva sin conocimiento oral.
- Riesgos/deuda remanente explícitos.
- Si Graphify está disponible en el entorno de desarrollo, el grafo del repositorio fue refrescado después de cambios estructurales; un fallo de Graphify no sustituye los gates de source/tests.


## Adaptive learning graph DoD
Cuando un cambio toca memoria aprendida, además:
- graph data tiene durable provenance y puede reconstruirse;
- retrieval aplica scope/compatibility antes de ranking;
- graph outage no cambia lifecycle/verdict correctness del run;
- stale/contradicted memory se revalida o invalida;
- no secrets ni policy derivada de untrusted web content;
- cold-vs-warm eval demuestra beneficio o documenta explícitamente que la optimización no fue validada.
