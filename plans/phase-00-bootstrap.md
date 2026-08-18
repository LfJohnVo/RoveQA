# Phase 00 — Repository Bootstrap

## Objective
Crear monorepo mínimo, tooling reproducible y skeleton de capas sin lógica falsa.

## Tasks
1. Inicializar backend con `uv`, Python compatible con dependencias, pyproject, ruff, type checker, pytest.
2. Crear package tree de Clean Architecture y tests vacíos/health test.
3. Inicializar frontend React/Vite/TypeScript con pnpm, ESLint, Vitest/RTL.
4. Crear Dockerfiles base y un `compose.yaml` mínimo con PostgreSQL, Redis, Temporal, Temporal UI y FalkorDB con volumen persistente; heavy inference behind profiles. No integrar Graphiti todavía: Phase 09 lo hace sobre este servicio.
5. Crear `Makefile` o `justfile` con comandos de bootstrap/test/lint/up/down/logs.
6. Añadir `.env.example`; no crear secretos reales.
7. Crear CI local script que ejecute backend/frontend checks.
8. Preparar `.gitignore` para outputs locales (`.roveqa/runs`, artifacts, browser state, caches y credential files) sin ocultar contratos/configuración de proyecto deliberadamente versionable.
9. Instalar Graphify como tool de desarrollo si está disponible (`uv tool install graphifyy`), construir el grafo inicial después del skeleton y verificar al menos una consulta estructural. No añadirlo a runtime deps.
10. Actualizar HANDOFF con comandos reales.

## Gates
- Backend import/health test verde.
- Frontend unit smoke test + build verde.
- `docker compose config` válido.
- Dependencies básicas levantan con healthchecks o existe issue explícito reproducible.
- FalkorDB usa named volume persistente y puede arrancar vacío sin afectar el bootstrap.
- No business logic ni fake architecture añadida sólo para llenar carpetas.
- Si Graphify está disponible: `graphify-out/graph.json` generado y una query documentada; si no, skip explícito en HANDOFF.
