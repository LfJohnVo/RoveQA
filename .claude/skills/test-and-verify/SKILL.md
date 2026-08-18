---
name: test-and-verify
description: "Ejecuta el gate final de una fase o cambio: lint, type checks, unit/integration tests, build, contract checks y actualizaciones de progreso. Usar antes de declarar un phase, feature o fix como terminado."
---
# Test and verify $ARGUMENTS

1. Determinar qué paquetes/capas fueron modificados.
2. Ejecutar los checks mínimos relevantes y luego el gate completo exigido por la fase.
3. No omitir un check porque sea lento sin documentar claramente que quedó pendiente; una fase no está completa con un gate requerido pendiente.
4. Si falla algo de forma inesperada, aplicar `systematic-debugging` para demostrar la causa raíz antes del fix; luego volver a ejecutar el check afectado.
5. Ejecutar `/architecture-guard` conceptualmente sobre el diff.
6. Si toca durability/browser/actions, aplicar checklist de `/durability-review`. Si toca learned memory/Graphiti/FalkorDB, verificar además cold-vs-warm, provenance, invalidation y graph-outage/rebuild según `adaptive-memory-graph`.
7. Actualizar `PROGRESS.md` y `HANDOFF.md` sólo con resultados realmente observados.
