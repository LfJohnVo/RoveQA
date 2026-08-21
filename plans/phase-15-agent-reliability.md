# Phase 15 — Agent Reliability

## Objective

Que el agente pueda apuntarse a **cualquier URL** y verificar una historia contra ella. Hoy
no puede, y la causa no es el tamaño del modelo: es que no logra abrir un sitio real, que lo
que ve de la página no incluye su contenido, y que la información que la decisión necesita
está en el proceso y no llega al planner.

Al cerrar esta fase, apuntar el agente a un sitio cualquiera y verificar un criterio de
texto tiene que funcionar. Phase 16 añade lo que el navegador observa y no entrega —estado
HTTP, errores de consola— y el barrido sin historia. Phase 17 añade el arquetipo
autenticado. Ninguna de las tres cambia de modelo.

### La evidencia que define la fase

Con los criterios en la meta y la página entera delante, el planner emite:

```json
{"action_type": "assert_text",
 "target": {"text": "Iniciar sesión"},
 "rationale": "…the page observation clearly includes the text 'Iniciar sesión'
   under a heading level 4, so asserting its presence confirms the goal is met."}
```

Acción correcta, literal correcto, razonamiento correcto — y el literal en `target.text`, un
campo que `assert_text` no lee. El dominio rechaza, `recover` vuelve a `plan`, y el bucle
consume el presupuesto. Un modelo mayor emitiría el mismo casi-acierto, porque nada en el
contrato dice que `value` es el campo.

**No es la peculiaridad de un sitio.** Se midió primero contra una aplicación interna
autenticada y después contra un sitio de marketing público sin login en ninguna parte: el
mismo `invalid_action`, la misma observación descartada, el mismo fallo sin clasificar. Los
hallazgos son del agente — y el segundo sitio, que nadie había usado para desarrollar, aportó
dos defectos más que el primero no podía revelar.

### Principio

Cada arreglo es fontanería de información o una suposición que no se sostiene fuera de
`localhost`. Nada aquí cambia de modelo ni afloja una invariante de arquitectura, durabilidad
o seguridad.

---

## ADRs requeridos

Se crean **antes** de implementar su slice, no después.

| ADR | Decisión | Slice |
| --- | --- | --- |
| 0011 | Esperas y timeouts por clase de acción: qué significa «la página está lista» | 2 |
| 0012 | Schema de acción como unión discriminada generada desde los frozensets del dominio | 4 |
| 0013 | Cuándo puede juzgarse un criterio determinista, y qué significa para el veredicto | 8 |
| 0014 | Semántica de policy read-only: el tipo decide lo prohibido, la escalada del modelo decide la verificación | 9 |

---

## Slices

### Slice 0 — Medida antes de tocar nada, y sobre más de un arquetipo

Sin una medida repetible, «agente QA automático» no es verificable y la fase no se puede
cerrar. Y si el set de referencia es un solo tipo de sitio, la fase optimiza para ese tipo
sin que nadie lo note — por eso los arquetipos entran aquí, en la medida, y no como una rama
de código más adelante.

1. `docs/status/AGENT_FINDINGS.md` — cada hallazgo con el run que lo produjo, para que la
   línea base quede escrita y no recordada.
2. *Reference story set* sobre la app de fixtures de `tests/target_app/`, cubriendo cuatro
   formas que hoy fallan por razones distintas:
   - **una página, criterio de texto** — el caso mínimo, y hoy imposible;
   - **varias páginas** (inicio → detalle → criterio en el detalle) — la forma normal en una
     landing o un blog, y hoy inexpresable: los criterios se juzgan contra «la página en la
     que el run terminó»;
   - **tras un formulario** — criterio visible sólo después de escribir y enviar;
   - **inalcanzable** — debe salir `blocked` con causa, nunca `failed`.
3. Un fixture que **simule la web real**, no `localhost`: respuesta lenta, imágenes de
   terceros que nunca terminan, y un overlay. Los dos defectos de la slice 2 son invisibles
   contra un servidor local instantáneo, y sin este fixture volverán.
4. `scripts/agent-baseline.sh`: corre el set N veces y emite JSON con distribución de
   veredictos, llamadas al modelo por criterio verificado y tasa de `invalid_action`.
5. Ejecutarlo y comprometer la línea base.

**Gates**
- El script corre sin GPU disponible y lo dice, en vez de reportar cero.
- La línea base reproduce el bucle: `invalid_action` > 0 y ninguna historia `passed`.
- El caso multi-página y el fixture lento fallan hoy por la razón esperada, documentada.

### Slice 1 — `docker compose up -d` deja el stack usable *(R3)*

Levanta todo *healthy* con la API devolviendo 500: nadie aplica las migraciones, y `/health`
responde `ok`, así que el síntoma no delata la causa.

1. Servicio `migrate` de un disparo (`alembic upgrade head`) en `compose.yaml`.
2. `api` y `worker` dependen de él con `condition: service_completed_successfully`.
3. README y `docs/GUIDE.md`: el camino de cinco minutos deja de mentir.

**Gates**
- Desde volumen vacío, `docker compose up -d` y `GET /api/v1/projects` devuelve 200 sin
  ningún comando intermedio.
- `make migrate` sigue sirviendo a quien ya tiene el stack arriba.
- `docker compose config --quiet` verde.

### Slice 2 — El agente puede abrir un sitio real *(el primer bloqueo)*

`DEFAULT_ACTION_TIMEOUT_MS = 10_000` es **una sola constante para todas las acciones**,
incluida la navegación, y `page.goto()` espera por defecto el evento `load`. Medido contra un
sitio de marketing público:

| `wait_until` | Tiempo |
| --- | --- |
| `load` — el default de `goto` | **23,1 s** |
| `networkidle` | 23,9 s |
| `domcontentloaded` | **0,3 s** |

El run murió en `Page.goto: Timeout 10000ms exceeded`, repetidamente, sin llegar a ver la
página. El contenido que el agente necesita estaba listo en 0,3 segundos: los 23 son
imágenes y etiquetas de terceros.

«Pulsa este botón» y «carga este sitio web» no son la misma escala de espera, y hoy comparten
una constante. Cualquier sitio con analítica, fuentes externas o un carrusel cae aquí — que
es la web entera fuera de `localhost`.

**ADR 0011** primero: qué significa «la página está lista» y a qué escala espera cada clase
de acción. Propuesta de partida — navegar espera `domcontentloaded`, que es lo que pone el
contenido y las affordances a disposición; la espera por red pasa a ser algo que una acción
puede pedir (`wait_for`) en vez de una condición implícita de toda navegación.

1. Separar el timeout de navegación del de interacción con un elemento.
2. Configurable por policy, con un default que sirva a la web real y no sólo a `localhost`.
3. Un timeout de navegación se clasifica: hoy sale `inconclusive` con `failure_kind: null` y
   la razón se conoce.

**Gates**
- Un run contra el fixture lento de la slice 0 abre la página y verifica.
- Un host inalcanzable sigue fallando, con causa y sin agotar el presupuesto.
- El default queda documentado con el número medido que lo justifica.

### Slice 3 — Desentrecomillar, en un solo sitio

`aria_snapshot` entrecomilla los valores que lo necesitan, y `parse_affordances` se queda las
comillas dentro de la URL:

```
/url: "#cookies-policy-customize"   ->   https://<host>/"#cookies-policy-customize"
/url: "#"                           ->   https://<host>/"#"
```

En el sitio medido, **3 de 41 affordances** salieron con URL malformada, y las tres eran
enlaces de ancla — que en una landing son la navegación principal.

**La misma comilla es una trampa para la slice 5.** El texto también viene entrecomillado
cuando lo necesita: `- text: "@2025 Empresa - All rights reserved"`. Si la extracción de
texto no desentrecomilla, un criterio que busque ese literal falla — y un criterio
determinista que falla **acusa al producto**. Un solo helper, usado por los dos caminos.

**Gates**
- Un enlace de ancla resuelve a una URL navegable.
- Un literal entrecomillado se puede usar como criterio y no produce un `failed` falso.
- Ninguna affordance sale con una comilla en la URL.

### Slice 4 — El schema hace inexpresable la acción inválida *(A1)*

La raíz de la decisión. `BrowserDecision` es plano y `required` viene vacío, así que la
decodificación guiada no puede impedir un `assert_text` sin `value`: la regla vive sólo como
prosa en el prompt y como validación *a posteriori* en el dominio.

**ADR 0012** primero. La decisión estructural es de dónde sale la verdad: los variantes se
**generan desde `NEEDS_TARGET`, `NEEDS_VALUE` y `READ_ONLY_ACTIONS`**, no se escriben a mano.
Es el patrón que `prompts.py` ya usa para que el texto no se separe de la regla; un schema a
mano se separaría igual.

1. Unión discriminada por `action_type`, un variante por acción, campos requeridos derivados
   de los frozensets.
2. Los variantes no exponen `target` cuando la acción no lo lee — hoy `assert_text` acepta un
   `target` que su ejecución ignora, y ese campo es exactamente donde el modelo puso el
   literal.
3. Test que falla si un miembro de un frozenset no tiene su variante: el drift se vuelve un
   gate, no una revisión.

**Riesgo, y por qué se mide aquí.** Una unión de ~17 variantes es una gramática grande para
xgrammar. Medir tiempo de compilación y latencia de primer token contra vLLM vivo **antes** de
seguir. Si el coste no es aceptable, estrechar la unión a las acciones que el plan necesita y
anotar en el ADR el número medido.

**Gates**
- Un `assert_text` sin `value` no se puede generar: se rechaza en generación, no en el
  dominio.
- `invalid_action` cae a 0 en el set de referencia.
- Latencia de primer token documentada, antes y después.

### Slice 5 — La observación lleva el texto de la página *(A2)*

`describe_page()` captura el árbol de accesibilidad y `parse_affordances()` se queda sólo con
los controles: el texto se descarta en el mismo método que lo obtuvo. Medido en dos sitios sin
relación entre sí — en una pantalla de aplicación, 883 caracteres crudos con los cuatro
criterios dentro y 235 entregados sin ninguno; en una landing pública, 9.183 crudos y 2.462
entregados: 41 controles y **nada** del contenido, que en una landing es justamente lo que hay
que probar.

1. `PageState` gana el contenido textual del snapshot (heading, paragraph, text), normalizado
   y **acotado por caracteres, no por tipo de nodo**: el cap debe morder en un data grid de
   diez mil filas, no en una página de 883 caracteres.
2. `describe()` lo renderiza en una sección propia, separada de los controles.
3. Pasa por el desentrecomillado de la slice 3 y por `_neutralize()`. Contenido de página es
   dato no confiable, y esta slice **amplía la superficie de inyección**: hace falta un test
   con instrucciones hostiles en el texto de la página, no sólo en el nombre de un control.
4. Contención de secretos: un valor tecleado puede aparecer en el snapshot. Extender
   `tests/browser/test_secret_containment.py` a prompt, log, artifacts y grafo **con el texto
   ya incluido**.

**Gates**
- El planner recibe los literales de la página, en los dos sitios de referencia.
- Un data grid grande no hace crecer la observación por encima del cap.
- Test de inyección verde: instrucciones en el texto de la página no cambian la acción.
- Ningún secreto tecleado aparece en prompt, log, artifact ni grafo.

### Slice 6 — El planner conoce los criterios de aceptación *(A3)*

Los `verification_hints` entran a `build_agent_graph` y aparecen en dos sitios: el parámetro
y el nodo final. `PlanningRequest` no tiene campo para ellos, así que el agente recibe
«avanza esta meta» sin saber qué contaría como cumplirla.

1. `PlanningRequest` gana los criterios (id, descripción, literal esperado si lo hay).
2. `prompts.py` los renderiza en su propia sección delimitada.
3. Un criterio sin literal se marca como tal: el planner debe saber que ése lo juzga un
   modelo y que no puede afirmarlo con `assert_text`.

**Gates**
- Con los criterios delante, el planner elige `assert_text` con el literal en `value`.
- Un criterio sin literal no produce un `assert_text` inventado.

### Slice 7 — El estado `[disabled]` sobrevive al parseo *(A4)*

El snapshot marca el estado — `button "…" [disabled]` — y `Affordance` no tiene campo para
él, así que el agente ve un botón que parece pulsable y paga un timeout entero por descubrir
que no lo es. Un formulario que habilita su botón sólo cuando los campos están completos es un
patrón corriente, y hoy el agente no puede verlo.

1. `Affordance` gana el estado; `parse_affordances` lo lee del snapshot.
2. `describe()` lo muestra.
3. La frontera no ofrece un affordance deshabilitado como tomable.

**Cuidado que esta slice no puede fallar.** `Affordance.key` alimenta `state_signature`. Si el
estado entra en la clave, **toda baseline de exploración y todo fingerprint del grafo cambia
de significado en silencio**. El estado va en el objeto y en la descripción, nunca en la
clave; el test lo fija.

**Gates**
- Un control deshabilitado se describe como tal y no entra en la frontera.
- La signature de un estado no cambia cuando cambia el `disabled` de un control.

### Slice 8 — Verificación determinista, continua y multi-página *(A5)*

No es una optimización: es lo que hace expresable una historia que recorre varias páginas —
la forma normal en una landing, un blog o una tienda. Hoy los criterios se juzgan contra «la
página en la que el run terminó», así que un criterio que se cumple en el paso 2 y otro en el
paso 5 no pueden cumplirse los dos. Y un `verification_hint` es una subcadena: comprobarlo no
cuesta inferencia.

**ADR 0013** primero, porque toca la semántica del veredicto y hay una razón buena que
conservar: en una historia de varios pasos, afirmar «pedido confirmado» contra la página donde
el run se quedó tirado sería reportar el sitio del accidente como desenlace.

La decisión a escribir: **acumular observaciones no es relajar el veredicto**. Propuesta — se
registra *dónde y cuándo* se observó cada literal, el veredicto sigue exigiendo que todos los
criterios se cumplan, y lo que se gana es precisión en el reporte, no permisividad. El ADR
debe decidir además si el orden importa: un criterio que sólo tiene sentido tras un paso previo
no debería darse por bueno antes.

1. Evaluar los hints en cada observación y acumular `(criterion_id, step, url, visto)`.
2. El reporte lleva el punto de observación en vez de «no se alcanzó» cuando lo hubo.
3. El corto-circuito de `goal_failure` se conserva para los criterios que **nunca** se
   observaron satisfechos.

**Restricción no negociable:** ninguna ruta nueva puede producir un `failed`. `failed` es el
único veredicto que acusa al producto, y esta slice añade caminos hacia el veredicto. El test
que lo fija va antes de la implementación.

**Impacto de contrato:** `roveqa.run-report.v1` gana campos. Revisar la política de
compatibilidad en `contracts/` y decidir en el ADR si aditivo basta.

**Gates**
- La historia multi-página del set de referencia llega a `passed`.
- El run de una sola página cierra en el primer paso, no en 25.
- Ningún camino nuevo produce `failed`; test dedicado.
- Un criterio nunca observado sigue reportándose como no alcanzado, con su `failure_kind`.
- Los fixtures de `contracts/examples/` validan contra el schema actualizado.

### Slice 9 — Una policy read-only puede navegar *(R2)*

`NAVIGATE` está en `READ_ONLY_ACTIONS` («actions that cannot change the target's state») y aun
así una policy read-only lo rechaza: el modelo marca `side_effect: true` y `policy_guard`
deniega. Con `temperature: 0.0` es reproducible — *todo* run read-only muere en su primer
`navigate`, y el veredicto culpa a `policy`, así que parece configuración del usuario. Es
además el modo natural para probar un sitio que no se quiere tocar, que es el caso de una
landing, un blog o una documentación.

**ADR 0014** primero, porque la escalada de un solo sentido es deliberada. El argumento del
código es evitar «un clic no verificado en Eliminar cuenta» — pero `click` no está en
`READ_ONLY_ACTIONS`, así que ese caso ya está protegido **por tipo**. La escalada sólo añade
poder marcar una acción genuinamente read-only, y su único efecto observado es dejar el modo
read-only sin salida.

Propuesta para el ADR: el **tipo** decide lo prohibido; la escalada del modelo eleva el
requisito de verificación e idempotencia sin convertir una acción read-only en prohibida.

1. `prompts.py` renderiza `READ_ONLY_ACTIONS`, como ya hace con los otros dos frozensets. Es
   la lista que evitaría el error y la única que no se le daba al modelo.
2. `policy_guard` según lo que decida el ADR.

**Gates**
- Un run con `destructive_actions: false` navega, observa y verifica criterios de texto.
- Un `click` sigue denegado bajo la misma policy.
- Test de regresión con la escalada del modelo activa.

### Slice 10 — Un fallo diagnosticable no se reporta como misterio *(R4)*

Tres causas distintas —`Locator.fill` timeout, `Page.goto` timeout, un target inexistente—
salieron todas `inconclusive` con `failure_kind: null`, aunque la razón se conoce y se imprime
en `deterministic_observation`. El producto distingue a propósito `blocked` («sabemos por qué y
no fue el producto») de `inconclusive` («nadie sabe por qué»); clasificar mal gasta la
distinción que hace creíble el reporte.

Un localizador que no resuelve es una decisión del modelo que no correspondía a la página →
`model`. Un timeout de navegación es del entorno → `environment`. Reutilizar los `FailureKind`
existentes: un valor nuevo en el enum sería cambio de contrato.

**Gates**
- Un timeout de localización sale `blocked` con kind, no `inconclusive`.
- Un timeout de navegación sale `blocked` con kind distinto del anterior.
- Ningún camino deja `failure_kind: null` con una razón conocida en la mano.

### Slice 11 — Cierre

1. `scripts/agent-baseline.sh` de nuevo; comparar contra la línea base de la slice 0.
2. **Un smoke contra un sitio público que no se usó para desarrollar.** Es el único gate que
   detecta el sesgo de haber afinado contra un sitio conocido — que es exactamente cómo
   nacieron los defectos de las slices 2 y 3.
3. `bash scripts/ci-local.sh` verde.
4. `README.md` y `CHANGELOG.md`: la limitación documentada («ninguna historia llega a
   `passed`, un modelo mayor es la variable») era un diagnóstico equivocado; reemplazarla por
   lo medido.
5. `PROGRESS.md` y `HANDOFF.md` con comandos ejecutados y resultados reales.

---

## Gates de fase

- **Apuntar el agente a una URL arbitraria y verificar un criterio de texto funciona.** Es la
  promesa de la fase; si esto no se cumple, la fase no cierra.
- Todas las historias del set de referencia terminan con veredicto correcto: las alcanzables
  `passed` —incluida la multi-página—, la inalcanzable `blocked` con su causa.
- `invalid_action` en 0.
- Llamadas al modelo por criterio verificado: bajan al menos un orden de magnitud respecto a
  la línea base.
- Ninguna ruta nueva puede producir `failed`.
- Un run read-only navega, observa y verifica.
- Ningún enlace de ancla se corrompe; ningún literal entrecomillado produce un `failed` falso.
- Contención de secretos y defensa de inyección verdes **con el texto de página incluido**.
- Las signatures de exploración no cambiaron de significado.
- `bash scripts/ci-local.sh` verde: backend, CLI, frontend, migraciones, build, compose.

---

## Fuera de alcance

**Lo que el navegador observa y no entrega** — estado HTTP, errores de consola, peticiones
fallidas — el barrido de sitio sin historia, los overlays de consentimiento y la semilla de
exploración: `plans/phase-16-any-site.md`.

**Runs autenticados** — `plans/phase-17-authenticated-runs.md`. Un arquetipo más, no la puerta
a los demás.

**Los defectos de las aplicaciones bajo prueba.** Los hallazgos que produjo la validación
sobre sitios reales —un formulario cuyos tipos de botón invertidos hacen que Enter descarte las
credenciales sin intentar entrar, un mensaje de campo obligatorio inalcanzable— son de esas
aplicaciones, no de esta plataforma. Van a un ticket de su equipo y sirven como caso de
regresión externo; quedan escritos en `docs/status/AGENT_FINDINGS.md` para eso.

**Cambiar de modelo.** Deliberadamente no. Si tras esta fase el set de referencia pasa con el
4B cuantizado, el techo no era el modelo — que es lo que la evidencia sugiere. Ahí sí tiene
sentido medir uno mayor, contra una línea base que existirá.
