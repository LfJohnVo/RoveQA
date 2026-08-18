# Session Handoff

## Current phase
00 — Bootstrap.

## Last stable state
Blueprint creado; no existe implementación de producto todavía.

## Plan activo
Phase 00 slices (en orden):
1. Repo hygiene: `.gitattributes` LF normalization + `.gitignore` extras.
2. Backend skeleton: uv + pyproject + ruff + mypy + pytest, package tree Clean Architecture, health test.
3. Frontend skeleton: Vite React-TS + pnpm + ESLint + Vitest/RTL smoke test + build.
4. Root `compose.yaml`: postgres/redis/temporal/temporal-ui/falkordb con healthchecks y named volumes; inference tras profiles.
5. Dockerfiles base (backend/frontend) verificados con build.
6. `Makefile` + `scripts/ci-local.sh` ejecutado end-to-end.
7. Graphify: build inicial del grafo + query documentada.
8. Actualizar PROGRESS/HANDOFF con comandos/resultados reales.

## Verified commands
Ninguno todavía.

## Decisions made
Ver `docs/adr/`.

## Known issues / risks
- Model/GPU compatibility must be validated on the actual target host before pinning images.

## Next exact action
En Claude Code: `/implement-phase 00`.

Blueprint note: Phase 09 now owns the adaptive memory graph. Do not implement it before its phase except maintaining ports/extensibility required by current phase.
