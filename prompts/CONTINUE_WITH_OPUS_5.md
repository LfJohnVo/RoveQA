# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-18): blueprint auditado y endurecido, **Phases 00-04 DONE** (Phase 04: 5/5 gates PASS). 247 tests backend verdes, 31 de ellos contra Chromium real. Siguiente: Phase 05 (LangGraph agent core).

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
   `make up` va primero: desde Phase 01 el gate incluye migraciones y falla si PostgreSQL no está arriba. Los tests de Temporal y Redis se saltan si esos servicios no responden, así que confirma que están healthy antes de fiarte del verde. `ci-local.sh` debe terminar en "ci-local: all green" (247 tests backend; tarda ~50s por los tests de browser). Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF:
   > Implement Phase 05 slice 1: define the LangGraph agent state schema and its PostgreSQL-backed checkpointer, reconciling it with the domain `checkpoints` table exactly as ADR 0009 specifies (RecoveryPoint rows referencing a LangGraph checkpoint id plus browser recovery data), before adding any node — the resume path is what every later node depends on.
   Phases 00-04 están cerradas: dominio, persistencia, UnitOfWork, idempotencia, FastAPI, Temporal, eventos durables, Redis coordination/realtime, RunPolicy y el browser gateway con recovery YA existen y están testeados. No los rehagas. El comando de arranque es `/implement-phase 05`. Lee `plans/phase-05-langgraph-agent-core.md`.
7. **No repitas side effects**: el stack compose ya se levantó y validó (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-api`/`roveqa-worker` ya compilan y corren; el grafo Graphify ya existe. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**: Phase 05 no está Done hasta que TODOS sus gates de `plans/phase-05-langgraph-agent-core.md` pasen. Al cerrar: `/test-and-verify 05`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md` con resultados reales, y DETENTE — no empieces Phase 06 sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md` (`durability-review` + `postgresql` + `backend-slice` + `browser-runtime` para esta fase), `.claude/rules/*` por path, ADR para toda decisión estructural nueva. Los vigentes son ADR 0009 (retry ownership / workflow shape) y ADR 0010 (transaction ownership); no los contradigas.

## Contexto crítico que no debes redescubrir

- Los contratos v1 en `contracts/` fueron endurecidos ANTES de implementarse (memory labels, RunPolicy resolution, Verdict, failed_step_id, path-traversal guard). Impleméntalos tal como están; cambiarlos requiere versionado explícito.
- `Verdict` y `RunStatus` ya están modelados con su mapping (`docs/02-domain-model.md`) y defendidos por CHECK constraints en la DB.
- **Commands reciben `UnitOfWork` y commitean; queries reciben el repository** (ADR 0010). Persistir y commitear va SIEMPRE antes de cualquier side effect externo.
- **El fan-out de eventos es best-effort y falla en silencio por diseño.** Un cambio de configuración de Redis puede romperlo sin poner ningún test en rojo: verifica end-to-end (`XLEN stream:run:{id}`), no sólo con la suite.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito, o el converter devuelve un dict y la anotación de retorno miente.
- **Un run no arranca sin RunPolicy resuelta** y las policies son inmutables. Cualquier test que arranque un run debe sembrar una: usa `seed_project_with_default_policy` / `DEFAULT_POLICY_PAYLOAD` de `tests/conftest.py`.
- El enforcement de browser vive en `GuardedBrowserGateway`, no en el adapter: el adapter Playwright debe entregarse **siempre** envuelto. Un test de arquitectura ya prohíbe importarlo desde Domain/Application/Interfaces, pero construirlo dentro de infrastructure y pasarlo hacia arriba sin envolver esquivaría esa regla.
- `perform_once` (verify-before-retry) ya existe en `application/services/side_effects.py`: úsalo para cualquier side effect nuevo en vez de reintentar a ciegas.
- El browser está probado pero **no cableado a ningún run**: conectarlo es justamente Phase 05.
- Python 3.13 vía uv (`backend/.python-version`); pnpm 10.34.5 pinneado en `frontend/package.json`. mypy corre en strict sobre `src` y `tests`, y pytest trata los warnings como errores.
