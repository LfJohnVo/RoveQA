---
name: implement-phase
description: Ejecuta una fase concreta del roadmap de Agentic Web QA de forma incremental, verificable y con handoff durable. Usar cuando se pida construir, continuar o completar una fase del proyecto siguiendo los archivos plans/phase-XX-*.md.
---
# Implementar fase $ARGUMENTS

1. Leer `CLAUDE.md`, `docs/status/PROGRESS.md`, `docs/status/HANDOFF.md`, `docs/17-implementation-roadmap.md` y el archivo `plans/phase-$ARGUMENTS-*.md` correspondiente.
2. Verificar que las dependencias/gates de fases anteriores estén cumplidas. Si no, corregir primero la mínima deuda bloqueante y documentarla.
3. Activar `ponytail`. Si existe un grafo Graphify fresco, consultarlo para localizar boundaries/dependencias relevantes. Consultar `docs/21-claude-skill-routing.md` y cargar las skills especialistas de los slices de la fase. En Phase 09 o cambios de learned memory, cargar explícitamente `adaptive-memory-graph`. Usar `brainstorming` sólo para decisiones importantes aún no resueltas.
4. Escribir o actualizar en `docs/status/HANDOFF.md` una sección `Plan activo` con 3-8 slices verificables.
5. Implementar un slice a la vez respetando Clean Architecture/MVVM.
6. Tras cada slice, ejecutar los tests/lint/type-check relevantes y corregir fallos antes de continuar.
7. Para cambios estructurales, crear ADR. No cambiar silenciosamente tecnologías fijadas.
8. Ejecutar los acceptance gates completos de la fase. Si Graphify está disponible y hubo cambios estructurales, ejecutar `graphify update .` y una query de sanity sobre el capability modificado.
9. Actualizar `docs/status/PROGRESS.md` con estado real y `HANDOFF.md` con: completado, comandos ejecutados, resultados, decisiones, riesgos y siguiente paso exacto.
10. Detenerse al completar la fase. No comenzar la siguiente sin instrucción explícita.
