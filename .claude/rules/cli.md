---
paths:
  - "cli/**/*.ts"
  - "cli/**/*.tsx"
  - "cli/package.json"
---
# CLI rules
- `cli/` es Interface/Delivery: consumir sólo el API público de FastAPI.
- Prohibir imports/calls directos a Playwright, Temporal SDK, LangGraph, PostgreSQL, Redis, vLLM/AirLLM.
- Mantener stdout puro en `--output json`; progress/debug/warnings a stderr.
- Validar responses críticas en runtime; no confiar sólo en TypeScript casts.
- Toda mutation reintentable conserva `Idempotency-Key`; persistent conflicts no se reintentan blindly.
- `wait` timeout/Ctrl-C detacha; nunca cancelar implícitamente.
- Limitar response body/history/page/file sizes; stream artifacts grandes.
- FailureBundle se valida por provenance y se finaliza atómicamente.
- Mantener CLI thin: no duplicar verification/business logic del backend.
