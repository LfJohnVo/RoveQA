# Phase 14 — Release Candidate

## Objective
Cerrar v1 operable en single-node, instalable por humanos y verificable por coding agents/CI.

## Tasks
1. Fresh-machine installation runbook.
2. Backup/restore for PostgreSQL/artifact directory and FalkorDB operational backup; additionally verify graph rebuild from PostgreSQL candidates so FalkorDB is not unique truth.
3. Upgrade/migration procedure.
4. Operator runbook for stuck/recovering runs.
5. Performance/capacity baseline for target hardware.
6. Final architecture/durability/security review.
7. Demo scenario and release checklist.
8. Public CLI install/runbook: install -> `roveqa setup` -> `roveqa doctor` -> plan scaffold/lint -> run create/wait -> artifact/failure.
9. Verify coding-agent skill installation in a fresh temporary repository without clobbering existing Claude instructions.
10. Contract compatibility check for published TestPlan/CLIEnvelope/FailureBundle schemas and example fixtures.
11. CI example producing machine-readable verdict and JUnit/summary adapter if implemented.
12. Release notes/changelog describing public contract versions and migration policy.
13. Knowledge-memory operations runbook: inspect sync lag, rebuild/validate graph, rotate embedding model, invalidate stale playbooks and confirm tenant isolation.

## Gates
- Si Graphify está disponible, refrescar el grafo final (`graphify update .`) y comprobar que las rutas arquitectónicas críticas pueden consultarse.
- Nuevo host puede levantar stack desde docs.
- Fresh external client puede instalar la CLI, pasar `roveqa doctor` y ejecutar el verification loop sin acceso directo a internals.
- Multi-hour soak run sin pérdida de progreso; durante el soak reiniciar al menos worker, Chromium y Redis según la matriz soportada.
- Backup/restore drill successful.
- Empty-FalkorDB rebuild drill successful and cold/warm memory benchmark results published in release evidence.
- FailureBundle de una falla de demo puede descargarse/materializarse y pasar integrity validation.
- Agent verification skill obtiene al menos un terminal verdict real en el demo y no declara success con un timeout/running state.
- All phase docs and status coherent.

## Required skills
- `test-and-verify`
- `architecture-guard`
- `durability-review`
- `api-design-principles` for final public contract review
- `changelog-generator` after all release gates are green
