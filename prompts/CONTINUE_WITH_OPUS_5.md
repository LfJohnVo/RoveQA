# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-18): blueprint auditado y endurecido, **Phases 00-05 DONE** (Phase 05: 3/3 gates PASS). 274 tests backend verdes. Siguiente: Phase 06 (vLLM model adapter/router).

## Pasos obligatorios, en orden

1. Lee `CLAUDE.md` completo. Sus invariantes de arquitectura, durabilidad, seguridad y skills routing gobiernan toda la sesión.
2. Lee `docs/status/PROGRESS.md` (estado por fase con evidencia).
3. Lee `docs/status/HANDOFF.md` completo — contiene decisiones tomadas, comandos ejecutados con resultados reales, gates PASS, known issues, deuda y riesgos.
4. Consulta Graphify si está disponible: existe `graphify-out/graph.json` fresco (code-only). Usa `graphify explain "<nodo>"` / `graphify query` antes de búsquedas amplias; verifica siempre el source antes de editar. El grafo NO incluye docs (falta LLM API key); no lo fuerces.
5. Verifica el last stable state antes de cambiar nada:
   ```bash
   make up
   make migrate
   bash scripts/ci-local.sh
   ```
   `make up` va primero: desde Phase 01 el gate incluye migraciones y falla si PostgreSQL no está arriba. Los tests de Temporal y Redis se saltan si esos servicios no responden, así que confirma que están healthy antes de fiarte del verde. `ci-local.sh` debe terminar en "ci-local: all green" (274 tests backend; tarda ~1 min por browser y checkpointer). Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF:
   > Implement Phase 06 slice 1: add a `ModelGateway` adapter for an OpenAI-compatible vLLM endpoint that returns *structured* planned actions validated against the closed browser action set, rejecting malformed model output with a typed error instead of coercing it — the graph already consumes this port, so nothing above it changes.
   Phases 00-05 están cerradas: dominio, persistencia, API, Temporal, eventos, Redis, RunPolicy, browser gateway con recovery, y el agent graph con checkpointer y resume YA existen y están testeados. No los rehagas. El comando de arranque es `/implement-phase 06`. Lee `plans/phase-06-vllm-router.md`.
7. **No repitas side effects**: el stack compose ya se levantó y validó (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-api`/`roveqa-worker` ya compilan y corren; el grafo Graphify ya existe. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**: Phase 06 no está Done hasta que TODOS sus gates de `plans/phase-06-vllm-router.md` pasen. Al cerrar: `/test-and-verify 06`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md`, y DETENTE — no empieces Phase 07 sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md` (`prompt-engineering-patterns` + `error-handling-patterns` + `durability-review` para esta fase), `.claude/rules/*` por path, ADR para toda decisión estructural nueva. Los vigentes son ADR 0009 (retry ownership / workflow shape) y ADR 0010 (transaction ownership); no los contradigas.

## Contexto crítico que no debes redescubrir

- Los contratos v1 en `contracts/` fueron endurecidos ANTES de implementarse (memory labels, RunPolicy resolution, Verdict, failed_step_id, path-traversal guard). Impleméntalos tal como están; cambiarlos requiere versionado explícito.
- `Verdict` y `RunStatus` ya están modelados con su mapping (`docs/02-domain-model.md`) y defendidos por CHECK constraints en la DB.
- **Commands reciben `UnitOfWork` y commitean; queries reciben el repository** (ADR 0010). Persistir y commitear va SIEMPRE antes de cualquier side effect externo.
- **El fan-out de eventos es best-effort y falla en silencio por diseño.** Un cambio de configuración de Redis puede romperlo sin poner ningún test en rojo: verifica end-to-end (`XLEN stream:run:{id}`), no sólo con la suite.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito, o el converter devuelve un dict y la anotación de retorno miente.
- **Un run no arranca sin RunPolicy resuelta** y las policies son inmutables. Cualquier test que arranque un run debe sembrar una: usa `seed_project_with_default_policy` / `DEFAULT_POLICY_PAYLOAD` de `tests/conftest.py`.
- El enforcement de browser vive en `GuardedBrowserGateway`, no en el adapter: el adapter Playwright debe entregarse **siempre** envuelto. Un test de arquitectura ya prohíbe importarlo desde Domain/Application/Interfaces, pero construirlo dentro de infrastructure y pasarlo hacia arriba sin envolver esquivaría esa regla.
- `perform_once` (verify-before-retry) ya existe en `application/services/side_effects.py`: úsalo para cualquier side effect nuevo en vez de reintentar a ciegas.
- **El worker no ejecuta episodios todavía**: falta un `ModelGateway` real, y la activity lo reporta en vez de simular. Inyectarlo en el container es justo el trabajo de Phase 06.
- El graph consume el port `ModelGateway`; nada por encima cambia al añadir el adapter real.
- **Windows: psycopg async exige `SelectorEventLoop` y Playwright exige `Proactor`.** Los tests del checkpointer conducen su propio loop; si el graph usa checkpointer y browser en el mismo proceso habrá que resolverlo. Es lo primero a validar en el slice 2.
- La tabla del dominio se llama `recovery_points`, no `checkpoints`: ese nombre lo ocupa LangGraph. `alembic/env.py` excluye las tablas que la librería gestiona; no las metas en el metadata.
- Si `uv add` falla con "Acceso denegado" en Windows, hay un proceso del venv vivo (uvicorn/python): ciérralo y reintenta.
- Python 3.13 vía uv (`backend/.python-version`); pnpm 10.34.5 pinneado en `frontend/package.json`. mypy corre en strict sobre `src` y `tests`, y pytest trata los warnings como errores.
