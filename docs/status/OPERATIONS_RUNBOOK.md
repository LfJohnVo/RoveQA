# Operations Runbook

Todo lo que hay aquí se ejecutó contra el stack real el 2026-08-20. Un runbook con
comandos que nadie corrió es una lista de deseos.

## Levantar el stack en una máquina nueva

Requisitos en el host: `docker compose` y `bash`. Nada más — el resto vive en
contenedores, incluidos los gates.

```bash
cp .env.example .env          # y ajustar lo que haga falta; ver los comentarios del fichero
make up                       # postgres, redis, temporal, falkordb
make migrate                  # aplica la cadena de Alembic desde una base vacía
docker compose up -d api worker frontend
bash scripts/ci-local.sh      # debe terminar en "ci-local: all green"
```

La UI queda en http://localhost:5173 y la API en http://localhost:8000.

**Sin GPU también funciona.** Sin `VLLM_BASE_URL` el worker arranca y dice honestamente
que no hay runtime de agente en vez de fingir decisiones. Con GPU:

```bash
docker compose --profile gpu up -d vllm
# y VLLM_BASE_URL=http://vllm:8000 VLLM_MODEL=<tag> en el entorno del worker
```

## Instalar la CLI como cliente externo

Lo que hace alguien que no tiene el repositorio. Ejecutado el 2026-08-20 en un contenedor
`node:22-alpine` limpio, sin acceso a los internals.

```bash
# 1. Obtener el paquete (quien publique el release adjunta el tarball)
npm install -g roveqa-cli-0.1.0.tgz

# 2. Apuntar a la instalación y guardar la configuración de este directorio
roveqa setup --api-url http://api:8000 --project <project-id>

# 3. Comprobar que hay con quién hablar, y que hablan el mismo contrato
roveqa doctor --output json          # exit 0 sano; 2 sin project; 8 con la API caída

# 4. Un plan de partida, validado contra el schema publicado
roveqa plan scaffold --output json > scaffold.json
node -e 'const d=require("./scaffold.json");require("fs").writeFileSync("plan.json",JSON.stringify(d.data,null,2))'
roveqa plan lint plan.json --output json

# 5. Ejecutar y esperar
roveqa run create --plan plan.json --idempotency-key <clave-estable> --output json
roveqa run wait <run-id> --timeout 10m --output json

# 6. Si falló, materializar la evidencia
roveqa run failure <run-id> --out ./bundle --output json
```

`roveqa --help` lista los comandos. Todo comando responde **un solo valor JSON** en stdout
con `--output json`; el progreso y los avisos van a stderr, y el exit code es parte del
contrato.

**Un timeout de `run wait` sale 7, no 0, y no cancela nada.** Verificado en el drill: la
espera del cliente venció, el proceso salió 7 diciendo cómo retomar, y el run siguió hasta
`completed` por su cuenta. Cancelar exige `roveqa run cancel`.

## Instalar el skill de verificación en un repo ajeno

```bash
cd /ruta/al/repo
roveqa agent install claude
```

Escribe `.claude/skills/roveqa-verify/SKILL.md` y añade un bloque a `CLAUDE.md`
**sin pisar lo que ya hubiera**: verificado sobre un repo con reglas propias, que seguían
intactas después, y una segunda instalación no las duplica.

## Backup

Se respalda lo que no se puede reconstruir: PostgreSQL y los bytes de evidencia.

```bash
./scripts/backup.sh                    # a backups/<timestamp>/
./scripts/backup.sh /ruta/que/prefiera
```

Deja `postgres.dump`, `artifacts.tar.gz`, la revisión de Alembic y un `MANIFEST.txt`.

**Lo que deliberadamente no respalda**, y por qué:

| Excluido | Motivo |
| --- | --- |
| FalkorDB | Proyección de conocimiento que PostgreSQL ya posee (ADR 0008). Un segundo respaldo sería una segunda copia libre de discrepar; se reconstruye tras restaurar |
| Temporal | Tiene su propio store y su propia historia de backup |
| Redis | Efímero por diseño: streams y locks, nada que perder |

## Restore

Destructivo a propósito: elimina y recrea la base de la aplicación. Un restore que
fusionara dejaría un estado que no es ni el backup ni lo que había antes.

```bash
./scripts/restore.sh backups/<timestamp>
```

Para y arranca `api` y `worker` alrededor de la operación, porque escribirían en medio.

**Después: reconstruir el grafo.** Queda vacío, que es lo esperado —es una proyección de
las filas que el restore acaba de reponer:

```bash
curl -X POST http://localhost:8000/api/v1/projects/<project-id>/memory/rebuild
curl      http://localhost:8000/api/v1/projects/<project-id>/memory/status
```

### Drill ejecutado (2026-08-20)

1. Estado inicial: 1 proyecto, 2 runs, 2 artifacts, revisión `8b3ac8f35fa4`.
2. `./scripts/backup.sh backups/drill2`.
3. Se creó un proyecto **después** del backup, como marcador.
4. `./scripts/restore.sh backups/drill2`.
5. Resultado: **1 proyecto, 2 runs, 2 artifacts**; el marcador **desapareció** —el restore
   reemplazó, no fusionó— y el screenshot volvió a descargarse por la API con sus 4 254
   bytes intactos (el repositorio verifica el hash al leer).

## Upgrade

Las migraciones son la parte con riesgo; lo demás es reconstruir imágenes.

```bash
./scripts/backup.sh                      # siempre antes
git pull
docker compose build api worker
make migrate                             # alembic upgrade head
docker compose up -d api worker frontend
bash scripts/ci-local.sh
```

Si una migración falla a mitad, restaurar el backup es el camino: `alembic downgrade` sólo
está verificado para la migración más reciente, no para saltos arbitrarios.

## Un run atascado

Diagnóstico, en orden de coste:

```bash
# 1. Qué dice el estado durable — la única fuente de verdad sobre un run
curl http://localhost:8000/api/v1/runs/<run-id>

# 2. Qué hizo, desde el log durable y no desde el stream efímero
curl "http://localhost:8000/api/v1/runs/<run-id>/events?after=0&limit=200"

# 3. Hasta dónde puede reanudar
docker compose exec -T postgres psql -U agentic -d agentic_qa \
  -c "select trigger, browser_url, created_at from recovery_points
      where run_id='<run-id>' order by created_at desc limit 5"

# 4. El worker
docker compose logs worker --since 15m | tail -50
```

**Un worker atascado se reemplaza; el run no se pierde.** No hay estado de run en su
memoria:

```bash
docker compose restart worker
```

**Cancelar es explícito.** Cerrar un cliente, un Ctrl-C en `roveqa run wait` o un timeout
no cancelan nada:

```bash
curl -X POST http://localhost:8000/api/v1/runs/<run-id>/cancel
```

Antes de sospechar del producto, mirar la clasificación: un run `blocked` con
`failure_kind` `policy`, `agent_budget` o `model` no encontró un defecto — no pudo hacer su
trabajo, y dice cuál de las tres cosas se lo impidió.

## Memoria adaptativa

```bash
BASE=http://localhost:8000/api/v1/projects/<project-id>/memory

curl      "$BASE/status?environment_id=<env>"     # cuánto se aprendió y cuánto está proyectado
curl -X POST "$BASE/validate?environment_id=<env>"  # busca desacuerdo, no lo repara
curl -X POST "$BASE/sync?environment_id=<env>"      # drena el backlog cuando el grafo vuelve
curl -X POST "$BASE/rebuild?environment_id=<env>"   # reconstruye desde PostgreSQL
```

`validate` es read-only a propósito: si reparara, la única forma de saber si el grafo está
sano sería reescribirlo, y eso destruye la evidencia de qué falló.

**Rotar el modelo de embeddings** invalida los vectores existentes, que se calcularon con
otro. Cambiar `EMBEDDING_MODEL` exige un `rebuild` después; hasta entonces el retrieval
sigue funcionando por texto y ranking determinista, más estrecho pero correcto.

Los cuatro responden desde PostgreSQL, así que siguen funcionando con el grafo caído —que
es justo cuando alguien los usa.

## Consultas operacionales

`backend/src/agentic_qa/infrastructure/observability/queries.py` tiene trece con nombre
—runs por estado, veredictos de la semana, duración p50/p95, distribución de
`failure_kind`, reducción del triage, edad del último checkpoint, backlog del grafo,
cobertura de exploración, huella de artifacts— y el suite las ejecuta contra el schema
real, así que ninguna miente por haber quedado desfasada.

## Qué esperar bajo carga

`docs/status/PERFORMANCE_PROFILE.md` tiene las cifras. Lo esencial: el estado de un run es
plano a partir de los 20 episodios (~1,2 KB) y el prompt también (~2 700 caracteres), así
que un run de mil episodios cuesta por paso lo mismo que uno de veinte. Las tablas de
checkpoint de LangGraph dominan el disco.
