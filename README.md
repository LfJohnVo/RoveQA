# RoveQA

QA agéntico de aplicaciones web, **local-first y self-hosted**. Le describes una historia
de usuario, y un agente la recorre en un Chromium real, la verifica y te deja evidencia
que alguien puede revisar.

Nada sale de tu máquina: el modelo corre en tu GPU, la evidencia en tu disco, la base de
datos en tu red. No hay cuenta que crear ni API key de nadie.

**Estado: `v1.0.0-rc`.** Las 15 fases del plan están cerradas con sus gates verdes.
[Qué promete y qué no](CHANGELOG.md).

---

## En cinco minutos

```bash
docker compose up -d
```

```bash
docker compose --profile gpu up -d vllm
```

Abre **http://localhost:5173**, pulsa *New project*, y dale un nombre y la dirección de tu
aplicación. Eso es todo lo que hace falta para empezar: la interfaz crea el proyecto con su
*run policy*, que es lo que decide a dónde puede ir un run y qué puede hacer allí.

Después: **Stories** → escribe una historia → **Compile plan** → **Start a run**.

¿Prefieres verlo funcionar sin escribir nada?

```bash
bash scripts/demo.sh
```

Dos historias contra la aplicación incluida, una que cumple y otra que no puede cumplir,
con el FailureBundle materializado y verificado al final.

---

## Qué hace

- **Verifica historias de usuario** contra tu aplicación, con un navegador de verdad, y
  mantiene separado lo observado de lo que un modelo opinó. Sólo una comprobación
  determinista puede acusar al producto; una hipótesis de modelo viaja etiquetada y al
  lado, nunca dentro.
- **Sobrevive a lo que se caiga.** Worker, Chromium, Redis, vLLM, FalkorDB y PostgreSQL
  tienen fila propia en [RECOVERY_MATRIX.md](docs/status/RECOVERY_MATRIX.md), cada una con
  el test que la demuestra. Verificado con 91 runs consecutivos bajo reinicios: ninguno se
  perdió.
- **Explora** una aplicación sola, acotada, y **sin gastar una llamada al modelo**; compara
  el mapa con la exploración anterior sin marcar cada cambio de DOM como novedad.
- **Agrupa fallos** antes de pedir explicaciones: veinte runs contra el mismo muro son un
  problema, no veinte.
- **Aprende** de runs verificados. La memoria durable vive en PostgreSQL; el grafo es una
  proyección que se puede reconstruir.
- **Programa regresiones** con schedules que sobreviven a un reinicio del stack.
- **Se opera desde la terminal** con salida machine-readable: un único valor JSON en
  stdout, diagnósticos en stderr, y un exit code que significa algo.

## Qué no hace todavía

- **Con el modelo incluido (Qwen3-4B) ninguna historia llega a `passed`.** El agente navega,
  lee la página, se corrige y captura evidencia; lo que no hace es declarar la meta
  alcanzada, así que el presupuesto lo detiene y el run sale `blocked`. Un modelo mayor es
  la variable, y probarlo no exige tocar código.
- Un run es un episodio: todavía no hay runs de varias horas.
- No es de alta disponibilidad. Es un despliegue de un nodo, deliberadamente.

El resto de límites conocidos está en el [CHANGELOG](CHANGELOG.md), escritos porque un
límite documentado es una decisión y uno tácito es una sorpresa.

---

## Tres maneras de usarlo

| | Para quién | Empezar por |
| --- | --- | --- |
| **Interfaz web** | Escribir historias, lanzar runs, mirar la evidencia | http://localhost:5173 |
| **CLI `roveqa`** | CI, scripts, uso diario desde la terminal | [Guía](docs/GUIDE.md#la-cli) |
| **Agente de código** | Que Claude verifique su propio trabajo | `roveqa agent install claude` |

La CLI habla **sólo** con la API pública de FastAPI: no importa Playwright, Temporal ni
PostgreSQL, y hay un test que lo comprueba contra una violación plantada.

---

## Documentación

| Documento | Para qué |
| --- | --- |
| **[Guía de uso](docs/GUIDE.md)** | **Empieza aquí.** De cero a un run con evidencia, con la interfaz y con la CLI |
| [Runbook de operaciones](docs/status/OPERATIONS_RUNBOOK.md) | Máquina nueva, backup/restore, upgrade, run atascado, memoria |
| [CHANGELOG](CHANGELOG.md) | Contratos públicos, política de migración, límites conocidos |
| [Release checklist](docs/status/RELEASE_CHECKLIST.md) | Qué se comprobó y con qué comando |
| [Matriz de recuperación](docs/status/RECOVERY_MATRIX.md) | Qué fallos están soportados y qué test lo prueba |
| [Perfil de rendimiento](docs/status/PERFORMANCE_PROFILE.md) | Qué cuesta un run largo |
| [Arquitectura](docs/01-architecture.md) | Cómo encaja todo |
| [Grafo del código](docs/22-codebase-graph.md) | El mapa navegable del repositorio |

## Cómo está construido

```
backend/    FastAPI · Clean Architecture · Temporal · LangGraph · Playwright
frontend/   React 19 · Vite · MVVM
cli/        TypeScript · sin dependencias del runtime
contracts/  Los tres schemas públicos, con ejemplo canónico cada uno
docs/       Especificación, arquitectura, ADRs y estado
plans/      Las 15 fases, todas cerradas
```

Las invariantes que no se negocian están en [CLAUDE.md](CLAUDE.md), y hay tests que las
hacen cumplir: el dominio no importa frameworks, las Views no importan clientes HTTP, la
CLI no importa el runtime. Un test lee los imports; no es una convención, es un gate.

Todo corre en contenedores. En el host sólo hacen falta `docker compose` y `bash`:

```bash
bash scripts/ci-local.sh
```

Termina en `ci-local: all green` — 946 tests backend, 149 CLI, 51 frontend, migraciones sin
drift, build de frontend y validación de compose.

---

## Construido con Claude Code

Este repositorio se construyó fase a fase con Claude Code, y las instrucciones siguen
siendo parte de él: [CLAUDE.md](CLAUDE.md) gobierna cada sesión, `plans/` tiene las 15
fases, y `.claude/skills/` las 20 skills project-scoped cuya matriz de precedencia está en
[docs/21-claude-skill-routing.md](docs/21-claude-skill-routing.md).

Dos son transversales: `ponytail` (mínimo cambio seguro, siempre activa) y `graphify`
(grafo de conocimiento del repositorio — distinto del Graphiti/FalkorDB que el producto usa
en runtime).

Para retomar el trabajo, [`prompts/CONTINUE_WITH_OPUS_5.md`](prompts/CONTINUE_WITH_OPUS_5.md)
es autosuficiente, y [`docs/status/HANDOFF.md`](docs/status/HANDOFF.md) tiene el estado real
con comandos ejecutados y resultados.
