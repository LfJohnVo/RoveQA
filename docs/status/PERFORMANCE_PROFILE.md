# Performance Profile

Qué crece con el **trabajo** de un run y qué crecía con su **duración**.

Un run de varias horas sólo es posible si dar un paso más cuesta lo mismo en el paso 5000
que en el paso 5. Estas son las mediciones de las tres cosas que están en ese camino: el
estado que carga un checkpoint, el prompt que lee el planner, y lo que ocupa en disco.

Reproducir:

```bash
docker compose --profile gates run --rm backend-tests python scripts/measure_growth.py
```

Las cifras son una foto; el gate es `backend/tests/test_growth_profile.py`, que asevera la
**forma** del crecimiento y sobrevive a cualquier cambio de redacción.

## El estado que carga un checkpoint

Medido el 2026-08-20, un episodio de 30 pasos cada uno.

| Episodios | Estado (bytes) | Prompt (chars) | Summaries en contexto | Plegados |
| --- | --- | --- | --- | --- |
| 1 | 430 | 862 | 1 | 0 |
| 10 | 782 | 1 681 | 10 | 0 |
| 20 | 1 182 | 2 611 | 20 | 0 |
| **200** | **1 212** | **2 717** | 20 | 180 |
| **1 000** | **1 234** | **2 717** | 20 | 980 |

Plano a partir de la ventana. Entre 200 y 1 000 episodios el estado crece 22 bytes y el
prompt no crece nada: la única diferencia son los dígitos de "N earlier episodes".

**Antes de esta fase no lo era.** `episode_summaries` no tenía cota, así que mil episodios
significaban mil summaries en *cada* checkpoint de *cada* superstep y en *cada* prompt —
del orden de 50 KB de estado en vez de 1,2 KB, unas 40× más, sobre la tabla que ya domina
el disco. Crecimiento con la duración disfrazado de compactación. Lo encontró escribir
este perfil, no revisar el código.

## Los pasos dentro de un episodio

| Pasos | Estado (bytes) |
| --- | --- |
| 10 | 430 |
| 100 | 430 |
| 5 000 | 432 |

La ventana de trabajo (`MAX_RECENT_STEPS = 12`) hace que un episodio de cinco mil pasos
pese lo mismo que uno de diez. Esos dos bytes son el `step_index`.

## Qué ocupa en disco

Las tablas mayores de la base de tests tras una corrida completa del suite:

| Tabla | Tamaño | Filas |
| --- | --- | --- |
| `checkpoint_writes` | 1 048 kB | 1 562 |
| `checkpoints` | 680 kB | 476 |
| `checkpoint_blobs` | 480 kB | 510 |
| el resto | ≤ 64 kB | ≤ 4 |

Los checkpoints de LangGraph dominan, y por eso el tamaño del estado importa más ahí que
en ningún otro sitio: cada superstep escribe una fila. Todo lo demás es ruido en
comparación — las tablas del dominio son diminutas porque guardan referencias, no bytes.

Los artifacts guardan **referencias** en PostgreSQL y los bytes en el filesystem
(docs/11), acotados por `MAX_ARTIFACT_BYTES` por artifact. Su crecimiento es con el
trabajo —una captura por episodio— y es el que se espera.

## Cuánto tarda un run entero, por forma

Medido con `scripts/agent-baseline.sh`, 3 repeticiones de cada forma, modelo real
(`Qwen/Qwen3-4B-Instruct-2507` en vLLM) contra la app de pruebas local. 18 runs, cero
timeouts en las dos columnas. Los datos crudos de la corrida actual están en
`baseline-phase16.json`.

| Forma | Antes (2026-08-21) | Después (2026-08-22) | |
| --- | --- | --- | --- |
| `one-page` | 3 passed, 26 s | 3 passed, **6 s** | 4,3× |
| `multi-page` | 3 passed, 26 s | 3 passed, **10 s** | 2,6× |
| `after-a-form` | 1 passed / 2 blocked, 42 s | **3 passed**, **11 s** | 3,8× |
| `unreachable` | 3 blocked, 32 s | 3 blocked, **6 s** | 5,3× |
| `sweep-only` | 3 passed, 5 s | 3 passed, 5 s | — |
| `story-and-sweep` | 3 passed, 5 s | 3 passed, 6 s | — |

`reachable_passed` pasó de 13/15 a **15/15**; `unreachable_never_failed: true` y
`timed_out: 0` en ambas. Ningún criterio se perdió: las formas alcanzables verifican
6/6, 12/12, 9/9, 15/15 y 9/9.

Las dos filas que no cambiaron son las que ya no usaban el modelo. Ahí está la lectura
de fondo: **lo que costaba tiempo era inferencia desperdiciada**, y las dos correcciones
son la misma corrección — el proceso ya sabía algo y no se lo decía a quien decidía.

### Lo que el planner pedía dos veces

El log de acciones de un run bloqueado de `after-a-form`:

```
1 | navigate | go to records page                      | ok=true
2 | fill     | set reference value                     | ok=true
3 | fill     | set the name of the record to 'Probe'   | ok=false | Locator.fill: Timeout 10000ms exceeded.
4 | fill     | set the name of the record to 'Probe'   | ok=false | Locator.fill: Timeout 10000ms exceeded.
5 | fill     | set the name of the record to 'Probe'   | ok=false | Locator.fill: Timeout 10000ms exceeded.
```

Rellenó el campo que el formulario sí tiene, inventó un segundo campo y lo pidió tres
veces idénticas: treinta segundos de timeout de locator para no aprender nada. El fallo
ya estaba en `recent_steps` como prosa y la prosa no lo detuvo, así que el locator vuelve
al prompt como un hecho — `PlanningRequest.failed_targets`, sección
`<targets_that_did_not_work>`, `planner.v7`. La navegación queda fuera a propósito: un
locator que no resuelve no va a resolver, pero una url que falló una vez pudo ir lenta.

### Lo que el planner pedía veinte veces

Corregido lo anterior, la forma pasó a 3/3 passed y el log mostró el desperdicio mayor:

```
1 | navigate     | go to records page   | ok=true
2 | fill         | set reference value  | ok=true
3 | fill         | set name             | ok=true
4 | click        | submit_record        | ok=true
5 | assert_text  | ac-created           | ok=true      <- respondido aquí
6..25 | assert_text | (el mismo literal, veinte veces más)
```

Veinte llamadas al modelo y veinte acciones después de tener la respuesta, hasta agotar
el presupuesto de acciones. El run reportaba `passed`, así que nada estaba mal: sólo
lento, que es el desperdicio que sobrevive a un suite verde. `criteria_seen` lo sabía
desde el paso 0 y nadie actuaba sobre ello.

Ahora el episodio termina cuando cada criterio que un substring puede responder ha sido
visto (`story_is_done`). Dos límites deliberados:

- **Un criterio sin literal no cuenta.** Lo juzga un modelo, y parar antes de preguntarle
  sería declarar cumplido algo que nadie comprobó.
- **No aplica mientras se explora.** Ahí la historia es una capa sobre un barrido (ADR
  0017), y el trabajo del barrido —¿cargan todas las páginas alcanzables?— no termina
  porque los criterios de la historia aparezcan temprano.

Lo que cuenta como cumplido no cambió: un avistamiento en cualquier página del run ya
acreditaba el criterio antes de esto. Lo único que cambió es cuándo se deja de buscar.

## Lo que sigue sin medirse

1. **Latencia de un checkpoint bajo carga.** Se conoce su tamaño, no cuánto tarda en
   escribirse con varios workers concurrentes. `open_checkpointer` abre y cierra conexión
   por episodio (deuda registrada), que es el primer sitio donde mirar si aparece.
2. **Materialización de un FailureBundle grande.** El bundle se escribe en staging y se
   promociona con un rename; nadie ha medido cuánto tarda con cientos de artifacts.
3. **Coste de retrieval de memoria** con un grafo grande. El benchmark de Phase 09 midió
   el beneficio (llamadas ahorradas), no el coste.
