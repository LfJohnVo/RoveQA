---
name: systematic-debugging
description: Investiga bugs, tests fallidos, crashes y comportamiento inesperado mediante un proceso root-cause-first antes de proponer fixes. Usar ante cualquier fallo no trivial en frontend, backend, Temporal, browser, Redis, DB o modelos.
---
# Systematic debugging

No adivinar fixes. Encontrar primero la causa raíz.

## Phase 1 — Reproduce and collect evidence
- Reproducir con el caso mínimo confiable.
- Capturar error exacto, logs, correlation/run/step IDs y condiciones de entorno.
- En sistemas distribuidos, instrumentar boundaries: API -> Temporal -> worker -> browser/model -> persistence.
- Distinguir síntoma de primera divergencia observable.

## Phase 2 — Trace the cause
- Seguir el dato/estado hacia atrás hasta el origen.
- Comparar con un flujo equivalente que funcione.
- Revisar cambios recientes y contratos, no sólo la línea que lanzó la excepción.
- Para retries/crashes, reconstruir el timeline durable y verificar idempotencia.

## Phase 3 — Test one hypothesis
- Escribir una hipótesis falsable.
- Hacer el cambio/experimento mínimo que la confirme o descarte.
- No mezclar varios fixes especulativos.
- Tras tres hipótesis fallidas, cuestionar el modelo mental o la arquitectura antes de seguir parcheando.

## Phase 4 — Fix and prevent regression
- Crear test que falle por la causa encontrada.
- Implementar el fix mínimo en la capa correcta.
- Ejecutar tests cercanos y gate relevante.
- Verificar que logs/errors siguen siendo útiles y no se ocultó el fallo.
- Documentar root cause y recovery si el incidente afecta operaciones largas.
