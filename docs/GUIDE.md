# Guía de uso

De cero a un run con evidencia. Todos los comandos de esta guía se ejecutaron contra el
stack real; si alguno no funciona en tu máquina, es un bug, no una errata.

- [Levantarlo](#1-levantarlo)
- [Tu primer proyecto](#2-tu-primer-proyecto)
- [Escribir una historia](#3-escribir-una-historia)
- [Lanzar un run y leerlo](#4-lanzar-un-run-y-leerlo)
- [Qué significa cada veredicto](#5-qué-significa-cada-veredicto)
- [La CLI](#6-la-cli)
- [En CI](#7-en-ci)
- [Que un agente de código verifique su trabajo](#8-que-un-agente-de-código-verifique-su-trabajo)
- [Regresiones programadas](#9-regresiones-programadas)
- [Explorar sin historia](#10-explorar-sin-historia)
- [Cuando algo va mal](#cuando-algo-va-mal)

---

## 1. Levantarlo

Necesitas Docker y `bash`. Nada más: todo lo demás corre en contenedores.

```bash
docker compose up -d
```

Levanta PostgreSQL, Redis, Temporal, FalkorDB, la API, el worker y la interfaz. Comprueba
que respondan:

```bash
docker compose ps
```

### El modelo

El agente necesita un endpoint de modelo. Con una GPU NVIDIA:

```bash
docker compose --profile gpu up -d vllm
```

La primera vez descarga el modelo (unos minutos). El worker tiene que saber dónde está:

```bash
VLLM_BASE_URL=http://vllm:8000 VLLM_MODEL=Qwen/Qwen3-4B-Instruct-2507 docker compose up -d worker
```

> **Esto es fácil de olvidar y el síntoma no lo delata.** Un worker sin endpoint no falla:
> ejecuta los runs *sin episodio* y los devuelve `inconclusive`. Si todos tus runs salen
> inconclusive en segundos, es esto. Ponlo en tu `.env` y deja de pensar en ello.

Qué modelos caben en tu tarjeta está en `.env.example`. Sin GPU el resto del sistema
funciona —proyectos, historias, planes, exploración, memoria, evidencia— pero un run no
puede planificar.

---

## 2. Tu primer proyecto

Abre **http://localhost:5173** y pulsa **New project**.

La consola usa el sistema de diseño de
[Windmill Dashboard](https://github.com/estevanmaito/windmill-dashboard) (MIT). El botón de
la luna/sol en la cabecera cambia entre claro y oscuro, y recuerda tu elección por encima de
lo que prefiera el sistema operativo.

Te pide cuatro cosas, y las cuatro importan:

**Nombre.** Para ti.

**Application origin.** `http://localhost:3000`, o donde viva tu aplicación. Es esquema,
host y puerto — sin ruta. Este campo hace dos trabajos: es la **valla** (un run que intente
salir de ahí es rechazado antes de ejecutar nada) y es la **información** (al planner se le
dice esta dirección; sin ella un run empieza en una página en blanco sin nada a lo que
apuntar).

> Si tu aplicación corre en tu máquina y el worker en un contenedor, `localhost` no es la
> misma cosa para los dos. Usa el nombre del servicio si está en el mismo compose, o
> `http://host.docker.internal:3000` desde el contenedor hacia el host.

**Let runs click, type and submit.** Apagado por defecto, y apagado significa que el agente
mira y no toca: cualquier clic se rechaza y el run termina. Enciéndelo sólo contra algo
cuyos datos no te importen.

**Presupuestos** — acciones, llamadas al modelo, segundos. Un run que agota uno se detiene
y reporta `blocked`. Nunca reporta un problema del producto que no terminó de mirar.

### El banner de cookies

Un quinto ajuste que sólo existe por API todavía: `consent`, con tres valores.

| valor | qué hace |
| --- | --- |
| `leave` (por defecto) | No lo toca. Si el sitio tapa el contenido con el banner, el run falla ahí y lo dice. |
| `reject` | Toma la opción **menos concesiva** que el banner ofrezca. Recomendado. |
| `accept` | Toma la que acepta. Nunca por defecto, nunca inferido. |

El default cuesta runs a propósito. Aceptar cookies es un acto legal hecho **en nombre de
alguien**, y "Accept all" es casi siempre el botón más fácil de encontrar — más grande, más
contraste, primero en el DOM. Cualquier heurística que optimice «pasar el banner» aterriza
en la opción que más concede, por diseño del sitio.

Un run que falla porque había un banner es un fallo visible con un remedio obvio. Uno que
aceptó rastreo calladamente en un sitio que no es tuyo es algo de lo que nadie se entera
hasta que se entera otro. Contra tu propio staging, pon `accept` y olvídate; el default
protege el caso en que el objetivo es de otra persona, que es para lo que existe Phase 16.

Detalle honesto: el reconocimiento es **por etiqueta**, no estructural. Un banner cuyos
botones digan "Sure" y "Maybe later" no se reconoce, y el run no adivina — lo reporta sin
tocar. [ADR 0018](adr/0018-consent-overlays.md) explica por qué y qué costaría hacerlo
estructural.

<details>
<summary>Lo mismo por API, si prefieres scriptearlo</summary>

```bash
curl -sS -X POST http://localhost:8000/api/v1/projects \
  -H 'content-type: application/json' -d '{"name":"Checkout"}'
```

```bash
curl -sS -X POST http://localhost:8000/api/v1/projects/$PROJECT/run-policies \
  -H 'content-type: application/json' \
  -d '{"allowed_origins":["http://localhost:3000"],"max_duration_seconds":300,
       "max_actions":20,"max_model_calls":20,"destructive_actions":true,
       "set_as_project_default":true}'
```
</details>

---

## 3. Escribir una historia

En el proyecto, **Stories**. Una historia es *como quién*, *qué quiere lograr* y **criterios
de aceptación**.

El criterio es donde se juega todo. Cada uno tiene:

- **Id** — `ac-order-confirmed`. Lo que aparecerá en el reporte.
- **Has to be true** — la frase en prosa.
- **Text the page must contain** — y aquí está la decisión que casi nadie ve al escribirla.

**Con texto**, el criterio se comprueba de forma determinista: la página lo contiene o no lo
contiene, y si no lo contiene el run **puede acusar al producto**.

**Sin texto**, lo juzga un modelo. Y una opinión de modelo nunca acusa al producto: lo mejor
que puede pasar es que el run quede `inconclusive`. Es una decisión legítima —hay cosas que
no se pueden expresar como una cadena— pero conviene tomarla a propósito. La interfaz te lo
advierte mientras escribes, no tres runs después.

Cuando la historia esté guardada: **Compile plan**. Eso produce un `TestPlan` inmutable
versionado por el hash de su contenido. Un run apunta a una versión concreta, así que
cambiar la historia mañana no cambia lo que significó el run de hoy.

---

## 4. Lanzar un run y leerlo

**Start a run**. La página del run se actualiza en vivo por WebSocket, y si recargas o
pierdes la conexión reconstruye el historial desde el log durable — el socket sólo lo hace
oportuno, no es la fuente de verdad.

Cuando termina verás, separados a propósito:

- **Lo observado** — qué comprobó, en qué página, con qué resultado.
- **La evidencia** — screenshots, con su hash y su tamaño.
- **La hipótesis del modelo**, si la hay, etiquetada como tal.

Esa separación es la regla central del producto. Una hipótesis de modelo va *al lado* de la
evidencia, nunca dentro, y nunca se presenta como observación.

---

## 5. Qué significa cada veredicto

| Veredicto | Qué pasó | Qué hacer |
| --- | --- | --- |
| `passed` | Todos los criterios se cumplieron | Nada |
| `failed` | Un criterio determinista no se cumplió | **Mirar el producto.** Es lo único que acusa |
| `blocked` | El run no pudo hacer su trabajo, y se sabe por qué | Mirar el `failure_kind` |
| `inconclusive` | El run no pudo, y no se sabe por qué | Mirar la evidencia |

`blocked` viene con un motivo en el vocabulario del reporte: `agent_budget` (se acabaron las
acciones, las llamadas o el tiempo), `policy` (la policy rechazó una acción), `model` (no se
pudo obtener una decisión utilizable), `environment`.

La diferencia entre `blocked` e `inconclusive` es deliberada: *"sabemos por qué y no fue el
producto"* no es lo mismo que *"nadie sabe por qué"*, y confundirlas es cómo un reporte deja
de ser creíble.

**Nada de esto acusa a tu aplicación excepto `failed`.** Si un run no llegó al criterio, el
sistema no comprueba la página de todas formas: reportaría lo que hubiera en pantalla como
si fuera el desenlace de la historia.

---

## 6. La CLI

La CLI es el mismo control plane visto desde la terminal, pensada para que la lea un
programa. Habla sólo con la API pública.

```bash
cd cli && pnpm install && pnpm build && npm link
```

O, si publicaste el release, `npm install -g roveqa-cli-0.1.0.tgz`.

```bash
roveqa setup --api-url http://localhost:8000 --project <project-id>
```

```bash
roveqa doctor --output json
```

`doctor` comprueba que hay con quién hablar **y que hablan el mismo contrato**. Sale 0 si
todo está sano, 2 si falta configuración, 8 si la API no responde.

El bucle completo:

```bash
roveqa plan scaffold --output json > scaffold.json
```

```bash
roveqa plan lint plan.json --output json
```

```bash
roveqa run create --plan plan.json --idempotency-key regresion-2026-08-20 --output json
```

```bash
roveqa run wait <run-id> --timeout 10m --output json
```

### Las tres reglas que conviene saber

**`--output json` es machine-pure.** Un único valor JSON en stdout; el progreso y los avisos
van a stderr. Puedes hacer `> verdict.json` sin filtrar nada.

**El exit code es parte del contrato**, no un detalle de implementación:

| | |
| --- | --- |
| `0` | pass |
| `1` | veredicto terminal que no es pass |
| `2` | configuración o uso |
| `4` | no encontrado |
| `5` | validación |
| `6` | conflicto (una idempotency key reusada con otra petición) |
| `7` | **tu espera venció; el run sigue vivo** |
| `8` | el entorno no está sano |

**Esperar no es poseer.** Un `--timeout` que vence, o un Ctrl-C, sólo desconectan al cliente:
salen 7 y te dicen cómo retomar. El run sigue. Cancelarlo exige pedirlo:

```bash
roveqa run cancel <run-id>
```

> `--timeout` son **milisegundos** si no pones unidad. Ponla siempre: `10m`, `300s`.

### Cuando algo falla

```bash
roveqa run failure <run-id> --out ./bundle --output json
```

Materializa un **FailureBundle**: un directorio con `manifest.json` y los artifacts que
describe. Se escribe de forma atómica —o está completo, o lleva una marca `.partial` que
dice que no lo está— y cada byte se comprueba contra el `sha256` del manifest antes de
tocar el disco. Nunca mezcla evidencia de dos runs.

```bash
roveqa run diff <run-a> <run-b> --output json
```

```bash
roveqa run flaky --plan plan.json --count 5 --output json
```

`roveqa --help` lista los 20 comandos.

---

## 7. En CI

Antes que nada, el token. Se emite en el host de RoveQA, una vez, y se muestra una vez:

```bash
docker compose exec api python -m agentic_qa.admin token issue --project <id> --label "github actions"
```

Ese valor va como secreto del repositorio en `ROVEQA_TOKEN`. No hay endpoint que emita
tokens y no lo habrá: emitir una credencial es un acto del host, así que no hay ruta que
filtrar ni token de administración cuyo robo escale de un proyecto a todos (ADR 0020).

**Un token alcanza su proyecto y ninguno más**, así que el pipeline de un repositorio no
puede tocar la aplicación de otro equipo, y revocar uno no corta a los demás:

```bash
docker compose exec api python -m agentic_qa.admin token revoke <token-id>
```

Si el valor se pierde, se emite otro y se revoca éste. Es la única recuperación honesta de
un secreto que nadie guardó.

Hay un workflow de ejemplo para las dos formas —
[`examples/ci/github-actions.yml`](../examples/ci/github-actions.yml) y
[`examples/ci/gitlab-ci.yml`](../examples/ci/gitlab-ci.yml) — y un adaptador a JUnit
distribuido **dentro del paquete de la CLI**:

```bash
roveqa run wait "$RUN" --timeout 30m --output json > verdict.json; echo $? > code
```

```bash
node "$(npm root -g)/roveqa-cli/examples/verdict-to-junit.mjs" verdict.json "$(cat code)" > junit.xml
```

La única regla que importa de ese adaptador: **no decide el resultado**. Sale con el código
que le dio la CLI. Un adaptador que reportara "los tests corrieron" mientras el run se quedó
sin tiempo convertiría en verde una pregunta que nadie respondió.

Cuatro salidas y cada una es una cosa distinta:

| Salida | Qué pasó |
| --- | --- |
| 0 | `passed` |
| 1 | veredicto terminal que no es pass — `failed`, `blocked`, `inconclusive` |
| 3 | el token falta, no vale, o es de otro proyecto |
| 7 | la espera venció; **el run sigue vivo** y la salida dice cómo retomarlo |

Un `blocked` no es un defecto: el run no pudo hacer su trabajo y dice por qué. Y un 3 trae
en `next_action` qué hacer al respecto, porque un pipeline en rojo a las tres de la mañana
no debería exigir leer esta guía.

---

## 8. Que un agente de código verifique su trabajo

```bash
cd /ruta/a/tu/repo && roveqa agent install claude
```

Escribe `.claude/skills/roveqa-verify/SKILL.md` y añade un bloque a tu `CLAUDE.md` **sin
pisar lo que ya hubiera**. Una segunda instalación no lo duplica.

A partir de ahí Claude puede lanzar un run y esperar un veredicto real. El skill le prohíbe
explícitamente declarar éxito con un timeout o con un run todavía corriendo — que es
exactamente lo que un agente hace si nadie se lo prohíbe.

---

## 9. Regresiones programadas

```bash
curl -sS -X POST http://localhost:8000/api/v1/projects/$PROJECT/schedules \
  -H 'content-type: application/json' \
  -d '{"schedule_id":"nightly","cron":"0 3 * * *","plan_id":"'"$PLAN"'"}'
```

Los schedules viven en Temporal y sobreviven a un reinicio del stack (verificado, no
supuesto). Un disparo termina en cuanto el run existe, así que una regresión más lenta que
su propio intervalo se apilará: dale margen al cron.

---

## 10. Explorar sin historia

Cuando no sabes todavía qué historias escribir, el agente puede recorrer la aplicación solo
y devolverte un mapa de estados y lo que cada uno ofrece.

**No gasta una sola llamada al modelo.** Decide qué probar a continuación desde lo que la
página ofrece, no desde una opinión. Y **termina siempre**, no por presupuesto sino por
construcción: una affordance se ofrece una única vez, así que dos páginas que se enlazan
mutuamente terminan igual que un sitio entero.

Comparar dos exploraciones te dice qué cambió de verdad entre dos versiones, sin marcar cada
diferencia de DOM como novedad.

---

## Cuando algo va mal

**Todos los runs salen `inconclusive` en segundos.** El worker no tiene endpoint de modelo.
Ver [arriba](#el-modelo).

**Todos los runs salen `blocked` con kind `policy`.** La policy no permite acciones con
efecto (`destructive_actions`), y el agente intentó hacer clic en algo.

**El agente nunca encuentra nada en la página.** Comprueba que el worker alcanza tu
aplicación por el origin que configuraste — no por el que tú usas en tu navegador. El
screenshot del bundle te lo dirá en un segundo: si muestra una página de error en vez de tu
aplicación, es eso. *(Nos pasó: durante noventa minutos el agente estuvo mirando un
"Blocked request" de Vite, y el screenshot fue lo que lo delató.)*

**Un run parece atascado.** El estado durable es la única fuente de verdad, y el runbook
tiene el procedimiento exacto:
[Un run atascado](status/OPERATIONS_RUNBOOK.md#un-run-atascado).

**Cualquier otra cosa.** El [runbook de operaciones](status/OPERATIONS_RUNBOOK.md) cubre
instalación en máquina nueva, backup y restore, upgrade y operaciones de memoria, con cada
comando ejecutado de verdad contra el stack.
