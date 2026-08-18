# Agentic Web QA — Claude Code Build Kit

Este repositorio de instrucciones define cómo construir **RoveQA** (working name): una plataforma agentica, local-first y self-hosted de QA y automatización web con ejecuciones durables de horas, memoria operacional y conocimiento reutilizable.

## Resultado esperado

Una aplicación self-hosted con:

- React + Vite + TypeScript para la UI.
- Una CLI `roveqa` agent-first y CI-friendly como adapter del control plane.
- FastAPI + Python para el control plane.
- Clean Architecture en backend.
- MVVM + Clean Architecture en frontend.
- Temporal para workflows durables.
- LangGraph para el state machine del agente y checkpoints persistentes.
- Playwright + Chromium para interacción web.
- vLLM para inferencia rápida y multimodal.
- AirLLM para análisis profundo/offline con modelos grandes.
- PostgreSQL como verdad durable.
- Redis para coordinación, locks, semáforos, hot cache y streams realtime.
- Graphiti + FalkorDB como **adaptive QA learning graph**: rutas, estados, playbooks, failures y feedback temporal reutilizable; reconstruible desde PostgreSQL.
- Filesystem inicialmente para screenshots, videos, HAR, traces y reportes.
- Docker + Docker Compose para desarrollo y despliegue single-node.

## Cómo usar este kit con Claude Code

1. Copia todo el contenido de este kit a la raíz de un repositorio Git vacío.
2. Revisa `CLAUDE.md` y `docs/00-product-spec.md`.
3. Abre Claude Code desde la raíz del repositorio.
4. Ejecuta `/implement-phase 00`.
5. No avances de fase hasta que todos los gates de la fase actual estén verdes.
6. Al terminar cada fase, exige la actualización de:
   - `docs/status/PROGRESS.md`
   - `docs/status/HANDOFF.md`
   - ADRs cuando haya una decisión nueva.
7. Para revisar límites arquitectónicos usa `/architecture-guard`.
8. Para revisar tolerancia a fallos usa `/durability-review`.
9. Para cerrar una fase usa `/test-and-verify`.
10. Consulta `docs/21-claude-skill-routing.md` para combinar las **20 skills** del proyecto.

## Orden de lectura para humanos

1. `docs/00-product-spec.md`
2. `docs/01-architecture.md`
3. `docs/02-domain-model.md`
4. `docs/03-clean-architecture.md`
5. `docs/04-frontend-mvvm.md`
6. `docs/05-durability-and-recovery.md`
7. `docs/17-implementation-roadmap.md`
8. `docs/24-testsprite-cli-evaluation.md`
9. `docs/25-agent-first-cli.md`
10. `docs/26-adaptive-learning-graph.md`
11. `docs/21-claude-skill-routing.md`
12. `plans/phase-00-bootstrap.md`

## Principio de trabajo

Claude Code debe implementar una fase a la vez. Cada fase debe dejar el repositorio compilable, testeable y con un handoff preciso. No se acepta una implementación enorme que sólo se valide al final.

## Skills incluidas

El kit incluye **20 skills project-scoped** en `.claude/skills/`:

- `adaptive-memory-graph`
- `api-design-principles`
- `architecture-guard`
- `backend-slice`
- `brainstorming`
- `browser-runtime`
- `changelog-generator`
- `durability-review`
- `error-handling-patterns`
- `frontend-design`
- `frontend-mvvm-slice`
- `graphify`
- `implement-phase`
- `interface-design`
- `ponytail`
- `postgresql`
- `prompt-engineering-patterns`
- `systematic-debugging`
- `test-and-verify`
- `vercel-react-best-practices`

La matriz de precedencia y combinación está en `docs/21-claude-skill-routing.md`.

## Claude Code codebase intelligence

Dos skills tienen un rol transversal:

- `ponytail`: disciplina always-on de mínimo cambio seguro para reducir sobreingeniería sin debilitar Clean Architecture, MVVM, durabilidad, seguridad ni tests.
- `graphify`: knowledge graph de desarrollo del repositorio. Es distinto del Graphiti/FalkorDB que usa el producto en runtime.

Después de Phase 00, instala Graphify como herramienta de desarrollo (`uv tool install graphifyy`) y construye/refresca el grafo según `docs/22-codebase-graph.md`.

## Evaluación de TestSprite CLI

Se evaluó `TestSprite/testsprite-cli` como posible base. La decisión arquitectónica está en `docs/24-testsprite-cli-evaluation.md` y ADR `0007`:

- **No** reemplazar el runtime RoveQA con TestSprite: el CLI público es un cliente hacia una plataforma hospedada y no contiene el browser/model/workflow engine local que requiere este producto.
- **Sí** incorporar patrones maduros de interfaz agent-first: planes versionados, JSON/exit codes estables, idempotency keys, `wait` desacoplado de `cancel`, failure bundles atómicos, dry-run, rerun/diff/flaky y skill de verificación para coding agents.

Estos cambios se implementan en **Phase 08 — Agent-First CLI and Verification Contracts**. El roadmap ahora termina en Phase 14. **Phase 09** construye explícitamente el adaptive learning graph y sus benchmarks cold-vs-warm.


## Adaptive learning graph (Phase 09)
RoveQA aprende de runs **verificados**, no de intuiciones del modelo. PostgreSQL conserva `knowledge_candidates`/feedback/provenance y Graphiti + FalkorDB materializa una proyección temporal consultable. Cada uso de memoria recibe feedback y puede ser revalidado o invalidado por fingerprint/version changes. El graph puede reconstruirse desde PostgreSQL.

Claude Code debe usar `adaptive-memory-graph` y `knowledge-engineer` en Phase 09. La especificación completa está en `docs/26-adaptive-learning-graph.md`.
