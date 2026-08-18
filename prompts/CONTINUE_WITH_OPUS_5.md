# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-18): blueprint auditado y endurecido, **Phases 00-03 DONE** y **Phase 04 IN_PROGRESS (2 de 5 slices)**. 216 tests backend verdes. Siguiente: Phase 04 slice 3 (test-target-app + adapter Playwright).

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
   `make up` va primero: desde Phase 01 el gate incluye migraciones y falla si PostgreSQL no está arriba. Los tests de Temporal y Redis se saltan si esos servicios no responden, así que confirma que están healthy antes de fiarte del verde. `ci-local.sh` debe terminar en "ci-local: all green" (216 tests backend). Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF:
   > Implement Phase 04 slice 3: create the deterministic `test-target-app` (a small local site with a form, a delayed response and a controlled 500) and the Playwright `BrowserGateway` adapter using semantic role/label locators with one BrowserContext per run, wiring it so callers only ever receive it wrapped in `GuardedBrowserGateway` — Playwright and Chromium are already installed, so no download is needed.
   Phase 04 slices 1-2 YA están hechos: Environment/RunPolicy con resolución normativa, action set tipado cerrado y `GuardedBrowserGateway`. No los rehagas. El comando de arranque es `/implement-phase 04`. Lee `plans/phase-04-browser-gateway.md`.
7. **No repitas side effects**: el stack compose ya se levantó y validó (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-api`/`roveqa-worker` ya compilan y corren; el grafo Graphify ya existe. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**: Phase 04 no está Done hasta que TODOS sus gates de `plans/phase-04-browser-gateway.md` pasen. Al cerrar: `/test-and-verify 04`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md` con resultados reales, y DETENTE — no empieces Phase 05 sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md` (`browser-runtime` + `postgresql` + `error-handling-patterns` + `durability-review` para esta fase), `.claude/rules/*` por path, ADR para toda decisión estructural nueva. Los vigentes son ADR 0009 (retry ownership / workflow shape) y ADR 0010 (transaction ownership); no los contradigas.

## Contexto crítico que no debes redescubrir

- Los contratos v1 en `contracts/` fueron endurecidos ANTES de implementarse (memory labels, RunPolicy resolution, Verdict, failed_step_id, path-traversal guard). Impleméntalos tal como están; cambiarlos requiere versionado explícito.
- `Verdict` y `RunStatus` ya están modelados con su mapping (`docs/02-domain-model.md`) y defendidos por CHECK constraints en la DB.
- **Commands reciben `UnitOfWork` y commitean; queries reciben el repository** (ADR 0010). Persistir y commitear va SIEMPRE antes de cualquier side effect externo.
- **El fan-out de eventos es best-effort y falla en silencio por diseño.** Un cambio de configuración de Redis puede romperlo sin poner ningún test en rojo: verifica end-to-end (`XLEN stream:run:{id}`), no sólo con la suite.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito, o el converter devuelve un dict y la anotación de retorno miente.
- **Un run no arranca sin RunPolicy resuelta** y las policies son inmutables. Cualquier test que arranque un run debe sembrar una: usa `seed_project_with_default_policy` / `DEFAULT_POLICY_PAYLOAD` de `tests/conftest.py`.
- El enforcement de browser vive en `GuardedBrowserGateway`, no en el adapter: el adapter Playwright debe entregarse **siempre** envuelto, o el control desaparece sin romper ningún test.
- Python 3.13 vía uv (`backend/.python-version`); pnpm 10.34.5 pinneado en `frontend/package.json`. mypy corre en strict sobre `src` y `tests`, y pytest trata los warnings como errores.
