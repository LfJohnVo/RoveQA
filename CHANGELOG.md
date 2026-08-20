# Changelog

## v1.0.0-rc — 2026-08-20

Primer candidato a release. RoveQA es una plataforma de QA agéntica, local-first y
autoalojada: recorre una aplicación web, verifica historias de usuario y produce evidencia
que alguien puede revisar.

### Contratos públicos

Tres, versionados, con schema JSON publicado en `contracts/` y un ejemplo canónico en
`contracts/examples/`:

| Contrato | Versión | Schema |
| --- | --- | --- |
| TestPlan | `roveqa.test-plan.v1` | `contracts/test-plan.schema.json` |
| CLIEnvelope | `roveqa.cli.v1` | `contracts/cli-envelope.schema.json` |
| FailureBundle | `roveqa.failure-bundle.v1` | `contracts/failure-bundle.schema.json` |

**Política de migración.** Un cambio **aditivo** —un campo opcional nuevo— no cambia la
versión. Un cambio que un consumidor v1 no pueda leer exige una versión nueva y un periodo
en el que el servidor hable las dos. No hay forma de actualizar en silencio un contrato que
otra gente ya está parseando, y `GET /api/v1/meta/contracts` existe para que un cliente
compruebe con qué está hablando en vez de suponerlo.

Los exit codes de la CLI son parte del contrato: `0` pass, `1` verdict terminal que no es
pass, `2` configuración, `4` no encontrado, `5` validación, `7` la espera del cliente venció
con el run vivo, `8` el entorno no está sano.

`--timeout` acepta unidad: `--timeout 300s`, `--timeout 10m`. Un número pelado sigue siendo
milisegundos, porque cambiar lo que significa hoy redefiniría en silencio lo que pidió cada
script existente; los ejemplos publicados usan unidad explícita.

### Qué hace

- **Verifica historias de usuario** contra una aplicación real, con Chromium, y separa lo
  observado de lo que un modelo opinó. Sólo un check determinista puede acusar al producto.
- **Sobrevive a lo que se caiga**: worker, Chromium, Redis, vLLM, FalkorDB y PostgreSQL
  tienen fila propia en `docs/status/RECOVERY_MATRIX.md`, cada una con el test que la
  demuestra.
- **Explora** una aplicación de forma autónoma y acotada, sin gastar una sola llamada a un
  modelo, y compara el mapa contra la exploración anterior sin marcar cada cambio de DOM.
- **Agrupa fallos** antes de pedir explicaciones: veinte runs contra el mismo muro son un
  problema, no veinte. Una hipótesis de modelo va **al lado** de la evidencia, nunca dentro.
- **Aprende** de runs verificados. La memoria vive en PostgreSQL; el grafo es una proyección
  reconstruible.
- **Programa regresiones** con schedules que sobreviven a un reinicio del stack.
- **Se opera desde la línea de comandos** con salida machine-readable: un valor JSON en
  stdout, diagnósticos en stderr, y un exit code que significa algo.

### Límites conocidos de este candidato

Escritos aquí porque un límite documentado es una decisión y uno tácito es una sorpresa:

- Un run es un episodio. Un run de varias horas todavía no es posible; el soak de release
  ejercita la propiedad de debajo sobre un flujo continuo de runs.
- Explorar exige un endpoint de modelo configurado aunque no lo llame nunca.
- Un disparo de schedule termina en cuanto el run existe, así que una regresión más lenta
  que su propio intervalo se apilará.
- No hay collector de métricas; las señales se consultan desde PostgreSQL
  (`infrastructure/observability/queries.py`).
- Los failure clusters y los state maps se leen por HTTP y no tienen interfaz.
- El análisis deep está implementado y verificado contra un modelo real, pero ningún modelo
  grande viene descargado: es `DEEP_MODEL` más una descarga.
- **Con el Qwen3-4B ninguna historia del demo termina en `passed`.** El agente navega la
  aplicación, lee sus elementos, se corrige cuando el dominio rechaza una acción y captura
  evidencia verificable; lo que no hace es declarar la meta alcanzada, así que el
  presupuesto lo detiene y el run sale `blocked` con kind `agent_budget`. El criterio no se
  comprueba contra la página cuando el agente no completó la historia — hacerlo reportaría
  lo que hubiera en pantalla como si fuera el desenlace. Un modelo mayor es la variable y no
  exige cambiar código.

### Para empezar

`docs/status/OPERATIONS_RUNBOOK.md` — instalación en máquina nueva, instalación de la CLI
como cliente externo, backup/restore, upgrade, run atascado y operaciones de memoria. Cada
comando de ese documento se ejecutó contra el stack real.
