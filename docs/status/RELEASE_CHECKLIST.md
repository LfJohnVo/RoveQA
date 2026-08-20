# Release Checklist

Lo que hay que poder afirmar antes de llamar a esto un release, y **cómo se comprueba cada
cosa**. Una casilla sin comando al lado es una opinión.

## Gates automáticos

| Comprobación | Comando | Estado |
| --- | --- | --- |
| Lint, tipos, migraciones y tests, todo en contenedores | `bash scripts/ci-local.sh` | ✅ `ci-local: all green` |
| Migraciones desde base vacía, sin drift | incluido en el gate (`alembic upgrade head` + `alembic check`) | ✅ |
| Los ejemplos publicados cumplen sus schemas | incluido en el gate (`cli-tests`) | ✅ |
| Los límites explícitos siguen siendo límites | incluido en el gate (`test_bounded_resources`, `file-inputs`) | ✅ |
| Las consultas operacionales siguen coincidiendo con el schema | incluido en el gate (`test_operational_queries`) | ✅ |
| El coste por paso no crece con la duración de un run | incluido en el gate (`test_growth_profile`) | ✅ |

## Drills, con evidencia

| Drill | Cómo | Evidencia |
| --- | --- | --- |
| Instalación en máquina nueva | `docs/status/OPERATIONS_RUNBOOK.md` | Cada comando ejecutado el 2026-08-20 |
| Cliente externo instala la CLI y llega a un verdict | contenedor limpio, `npm install -g` del tarball | `doctor` 0/2, `plan lint` 0, `run create` 0, `run wait` 7 con el run vivo |
| El skill de verificación no pisa instrucciones existentes | `roveqa agent install claude` en un repo con `CLAUDE.md` propio | La regla previa intacta; segunda instalación no duplica |
| Backup y restore | `scripts/backup.sh` + `scripts/restore.sh` | Marcador creado después del backup **desaparece**; artifact vuelve con sus 4 254 bytes |
| El artifact de un fallo se descarga por la API | `GET /api/v1/artifacts/{id}` | 200, PNG de 4 254 bytes que capturó el worker |
| Rebuild del grafo desde PostgreSQL | `POST /projects/{id}/memory/rebuild` | Probado en Phase 09 y tras el restore |
| Soak con perturbaciones | `scripts/soak.sh 90` | Ver abajo |
| Demo de extremo a extremo | `scripts/demo.sh` | Ver abajo |

## Soak de release (2026-08-20)

90 minutos, un run programado por minuto, perturbando en rotación el worker (que se lleva
Chromium) y Redis (`FLUSHALL` + reinicio) cada 10 minutos.

**Desviación declarada:** el plan pide un "multi-hour run"; hoy un run es un episodio, así
que un solo run no puede durar horas. La propiedad de debajo —que no se pierde progreso
mientras los servicios van y vienen— se ejercita sobre un flujo continuo de runs.

Resultado final: **91 runs, 91 terminales, 0 atascados**, con 8 perturbaciones. Ninguna
costó un run.

## El demo de release (2026-08-20)

`scripts/demo.sh`: dos historias contra la aplicación incluida, una que cumple y otra que
no puede cumplir. Todo lo posterior al setup pasa por la CLI.

**Qué demuestra hoy, comprobado:** el agente navega la aplicación real, lee sus elementos,
se corrige cuando el dominio le rechaza una acción, y produce un FailureBundle cuyo
`manifest.json` describe bytes que **verifican por sha256**. Los verdicts son terminales y
el exit code es 1, nunca un éxito falso.

**Qué no demuestra:** ninguna de las dos historias termina en `passed`. Con el Qwen3-4B en
esta máquina el planner trabaja la página y nunca declara la meta alcanzada; el presupuesto
lo detiene y el run sale `blocked` con kind `agent_budget`. Eso es exacto: el criterio no
se comprueba contra la página cuando el agente no completó la historia, porque
*"checking the page anyway would report whatever happened to be on screen as if it were the
outcome of the story"*. Un modelo mayor es la variable, y no hay que cambiar código para
probarlo.

## Los cinco defectos que encontraron el soak y el demo

Ninguno apareció revisando código. Los cinco tienen la misma forma: **algo que el sistema
sabía y no le decía a quien tenía que usarlo.**

1. **Nadie le decía al planner dónde está la aplicación.** Los origins de la RunPolicy eran
   sólo una valla; el planner adivinaba URLs que el mismo allowlist rechazaba. Ningún run
   salía de `about:blank`.
2. **Nadie le decía al planner qué necesita cada acción.** El dominio exige target semántico
   en `click`/`fill`/`wait_for` y url en `navigate`; el prompt listaba nombres de acciones y
   nada más. 91 de 91 runs del soak murieron por eso.
3. **Nadie le mostraba la página al planner.** `<page_observation>` era la URL. Se le pedía
   nombrar un elemento sin haberle enseñado ninguno, así que los inventaba, y cada invención
   costaba un timeout de locator. `describe_page()` existía desde Phase 12 y no estaba en el
   camino que planifica.
4. **Una propuesta rechazada mataba el run.** Un modelo inalcanzable y una propuesta que
   *nosotros* rechazamos llegaban como el mismo string. Ahora se distinguen: la segunda pasa
   por Recover con el motivo a la vista.
5. **El adaptador rechazaba objetivos correctos.** El strict mode de Playwright falla cuando
   un texto coincide dos veces, que en una página real es lo normal. El planner nombraba algo
   que existe y aprendía que nombrar cosas no funciona.

Y uno de despliegue, que la propia evidencia delató: el dev server de Vite respondía
**"Blocked request. This host ("frontend") is not allowed"** a todo el stack. El screenshot
del FailureBundle era esa página. Durante todo el soak el agente no estuvo mirando la
aplicación ni una sola vez.

## Antes de etiquetar

- [ ] `bash scripts/ci-local.sh` verde en la máquina que va a publicar
- [ ] `scripts/backup.sh` ejecutado y guardado fuera de la máquina
- [ ] `CHANGELOG.md` refleja las versiones de los tres contratos públicos
- [ ] `docs/status/PROGRESS.md` y `HANDOFF.md` coherentes con lo que hay
- [ ] Los límites conocidos del `CHANGELOG.md` siguen siendo los reales
- [ ] `npm pack` en `cli/` y el tarball adjunto al release

## Lo que este release no promete

- Alta disponibilidad: es un despliegue de un solo nodo, deliberadamente.
- Multi-tenancy más allá del aislamiento por proyecto que la memoria ya verifica.
- Que un modelo pequeño baste. El 4B planifica y a menudo propone acciones que el dominio
  rechaza —correctamente— y eso deja runs en `blocked` con kind `model`. Es una propiedad
  del modelo, no un defecto del sistema, y un modelo mayor la mejora.
