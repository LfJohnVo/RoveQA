# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-18): blueprint auditado y endurecido, **Phase 00 DONE con todos los gates verdes**, Phase 01 sin empezar.

## Pasos obligatorios, en orden

1. Lee `CLAUDE.md` completo. Sus invariantes de arquitectura, durabilidad, seguridad y skills routing gobiernan toda la sesión.
2. Lee `docs/status/PROGRESS.md` (estado por fase con evidencia).
3. Lee `docs/status/HANDOFF.md` completo — contiene decisiones tomadas, comandos ejecutados con resultados reales, gates PASS, known issues, deuda y riesgos.
4. Consulta Graphify si está disponible: existe `graphify-out/graph.json` fresco (code-only). Usa `graphify explain "<nodo>"` / `graphify query` antes de búsquedas amplias; verifica siempre el source antes de editar. El grafo NO incluye docs (falta LLM API key); no lo fuerces.
5. Verifica el last stable state antes de cambiar nada:
   ```bash
   git log --oneline -8
   git status
   bash scripts/ci-local.sh   # debe terminar en "ci-local: all green"
   make up                    # levanta postgres/redis/temporal/temporal-ui/falkordb
   ```
   Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF:
   > Implement Phase 01 slice 1: Run domain entity with RunStatus/Verdict state machine (per docs/02 including the new Verdict mapping) plus unit tests covering legal/illegal transitions, in `backend/src/agentic_qa/domain/runs/`, before touching SQLAlchemy or Alembic.
   El comando de arranque es `/implement-phase 01`. Lee `plans/phase-01-domain-postgres.md` y trabaja slice a slice.
7. **No repitas side effects**: el stack compose ya se levantó y validó en la sesión anterior (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-backend:dev`/`roveqa-frontend:dev` ya compilan; el grafo Graphify ya existe. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**: Phase 01 no está Done hasta que TODOS sus gates de `plans/phase-01-domain-postgres.md` pasen (domain unit tests de invariants, migración desde DB limpia a head, cero imports ORM en Domain/Application, repository contract tests). Al cerrar: `/test-and-verify 01`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md` con resultados reales, y DETENTE — no empieces Phase 02 sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md` (`backend-slice` + `postgresql` + `error-handling-patterns` para esta fase), `.claude/rules/*` por path, ADR para toda decisión estructural nueva (el último es ADR 0009 — retry ownership/workflow shape/checkpoints; no lo contradigas).

## Contexto crítico que no debes redescubrir

- Los contratos v1 en `contracts/` fueron endurecidos ANTES de implementarse (memory labels, RunPolicy resolution, Verdict, failed_step_id, path-traversal guard). Impleméntalos tal como están; cambiarlos requiere versionado explícito.
- `Verdict` (passed/failed/blocked/inconclusive/cancelled) es un domain value separado de `RunStatus`; el mapping está en `docs/02-domain-model.md`. Phase 01 debe modelar ambos.
- Python 3.13 vía uv (`backend/.python-version`); pnpm 10.34.5 pinneado en `frontend/package.json`. mypy corre en strict.
- El único retry owner por capa está fijado en ADR 0009; los durability tests de fases futuras dependen de esa forma.
