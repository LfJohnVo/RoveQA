---
paths:
  - "**/tests/**"
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*.spec.ts"
---
# Testing rules
- Testear comportamiento y contratos, no detalles internos triviales.
- Unit tests para Domain/Application; integration tests para adapters; system tests para workflows críticos.
- Cada bug real debe dejar un regression test cuando sea reproducible.
- Durability tests deben matar/reiniciar workers o simular activity retry en puntos con side effects.
- Contract tests machine-facing deben cubrir malformed responses, exit codes y schema/version drift, no sólo happy path.
- Para CLI probar procesos reales/subprocess cuando import-level tests no capturen stdout/stderr/signal semantics.
- FailureBundle tests deben intentar cross-run/cross-evidence contamination y partial writes.
- No usar sleeps arbitrarios cuando exista una condición observable.
