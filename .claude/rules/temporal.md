---
paths:
  - "backend/**/*temporal*.py"
  - "backend/**/workflows/**/*.py"
  - "backend/**/activities/**/*.py"
---
# Temporal rules
- Workflows deben ser deterministas.
- Network, DB, filesystem, browser e inferencia ocurren en Activities, no directamente en Workflow code.
- Definir timeouts y retry policy conscientemente.
- Heartbeats para activities largas.
- Side effects deben tener idempotency key o verify-before-retry.
- Nunca asumir que una Activity fallida no produjo efectos externos.
