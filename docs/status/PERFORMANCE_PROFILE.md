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

## Lo que sigue sin medirse

1. **Latencia de un checkpoint bajo carga.** Se conoce su tamaño, no cuánto tarda en
   escribirse con varios workers concurrentes. `open_checkpointer` abre y cierra conexión
   por episodio (deuda registrada), que es el primer sitio donde mirar si aparece.
2. **Materialización de un FailureBundle grande.** El bundle se escribe en staging y se
   promociona con un rename; nadie ha medido cuánto tarda con cientos de artifacts.
3. **Coste de retrieval de memoria** con un grafo grande. El benchmark de Phase 09 midió
   el beneficio (llamadas ahorradas), no el coste.
