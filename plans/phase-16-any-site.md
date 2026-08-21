# Phase 16 — Any Site

## Objective

Phase 15 deja al agente capaz de abrir cualquier URL y verificar una historia. Esta fase le da
lo que el navegador **ya observa y no entrega** —estado HTTP, errores de consola, peticiones
fallidas— y añade la forma de QA que un sitio de contenido realmente necesita: un barrido sin
historia y sin modelo.

No hay detección de arquetipos ni ramas por tipo de sitio, y nada se ajusta a mano por dominio.

## De dónde salen estos hallazgos

Se midieron apuntando el agente a **un sitio de marketing público cualquiera**, uno que nadie
había usado para desarrollarlo. Esa es la disciplina que la fase hereda de la anterior: la
generalidad no se revisa, se mide contra sitios que no se eligieron.

---

## Los dos huecos

### 1. El estado HTTP se descarta

`page.goto()` devuelve una `Response` con `.status` y el gateway ignora el valor de retorno.
`ActionOutcome` no tiene campo para él, y `succeeded` sólo dice si Playwright lanzó excepción.
**Un run no distingue un 200 de un 404 ni de un 500**: navega a una página de error, ve lo que
renderiza y lo toma por el sitio.

Para una landing o un blog, «ninguna página está rota» *es* la pregunta de QA, y hoy no se
puede formular. Es además el mecanismo exacto de la anécdota que la guía cuenta como cicatriz
—noventa minutos mirando un «Blocked request» de Vite—: el estado estaba en la respuesta.

### 2. Los errores de consola y las peticiones fallidas se capturan y nadie los lee

`ObservedFailures` acumula `console_errors` y `failed_requests` en el gateway y **no tiene un
solo consumidor** fuera de ese archivo. Un JS que revienta o una imagen que devuelve 404 son
señal de QA de primera clase en cualquier sitio, y ya están medidas.

---

## El problema de fondo: una landing no tiene historia

Los criterios se juzgan contra una historia con actor y meta. En un sitio de contenido eso casi
nunca es lo que se quiere saber: la pregunta es *«todas las páginas alcanzables cargan, tienen
título, no tienen errores de consola y ningún enlace interno está roto»*. No hay actor, ni meta,
ni criterio de aceptación — y no hace falta un modelo para responderla.

La exploración ya enumera los estados alcanzables y termina por construcción. Con el estado HTTP
y las fallas observadas, ese recorrido **es** el barrido de salud del sitio. La capacidad está
casi construida.

Y una observación más de la web real: el **banner de consentimiento fue lo primero que el agente
vio** — `heading "We use cookies"`, con «Only essentials» y «Accept all» como sus dos primeras
affordances. Es casi universal en la web pública, tapa contenido e intercepta clics, y hoy nada
lo cierra.

---

## ADRs requeridos

| ADR | Decisión |
| --- | --- |
| 0015 | Estado HTTP y fallas observadas en el resultado de una acción, y qué veredicto merece un 5xx |
| 0016 | Barrido de sitio: un modo de run sin historia, con comprobaciones deterministas por estado |
| 0017 | Overlays de consentimiento: qué puede cerrar un run y bajo qué decisión de policy |

---

## Slices

### Slice 1 — El navegador entrega lo que ya observa

**ADR 0015** decide lo que no es obvio: qué veredicto merece un 5xx. Un 500 en la aplicación
bajo prueba **es** un defecto del producto, así que es uno de los pocos caminos que pueden
justificar `failed` — y por eso se escribe antes de implementarse. Un 404 al navegar a una URL
que el modelo inventó no es lo mismo que un 404 en un enlace que el sitio ofrece; el ADR tiene
que separarlos.

1. `ActionOutcome` gana el estado HTTP; el gateway deja de descartar el retorno de `goto()`.
2. `ObservedFailures` llega al resultado del episodio, acotado y **redactado** — una URL fallida
   puede llevar un token en la query.
3. `PageState` lleva el estado, para que la observación diga si el planner está mirando una
   página de error. Hoy no puede saberlo.

**Gates**
- Un `navigate` a un 404 no vuelve como `succeeded` sin más.
- Un 5xx produce el veredicto que el ADR decida; test dedicado.
- Un error de consola aparece en el reporte, separado de las conclusiones del modelo.
- Ningún token en una URL fallida llega al reporte sin redactar.

### Slice 2 — La exploración sale de `about:blank` *(R1)*

Un run con `explore: true` no puede mapear nada: el grafo va de `START` a `explore`, que
describe la página actual, y el navegador llega recién abierto. Nada en producción navega a la
aplicación; el gate de Phase 12 pasa porque el propio test hace la navegación
(`test_exploring_a_real_app.py:60`).

Depende de las slices 2 y 9 de Phase 15: sin el timeout arreglado la semilla muere, y sin la
policy read-only arreglada se rechaza.

1. Semilla desde el origen de la policy — la misma fuente que ya alimenta la pista del planner.
2. Pasa por el browser guardado y cuenta como acción.
3. El test de Phase 12 deja de navegar por su cuenta: si producción no lo hace, el gate no debe
   taparlo.

**Gates**
- Una exploración mapea más de un estado sin ayuda del test.
- Un origen inalcanzable sale `blocked` con causa, no `frontier_exhausted`.

### Slice 3 — Barrido de sitio

**ADR 0016** primero: es un modo de run nuevo. Qué comprobaciones son universales, si el usuario
puede añadir las suyas, y cómo se reporta un hallazgo que no pertenece a ningún criterio de
aceptación porque no hay historia.

Comprobaciones por estado visitado, deterministas y sin una sola llamada al modelo:

- estado HTTP de la respuesta;
- que la página tenga título y un encabezado de primer nivel;
- errores de consola y peticiones fallidas;
- enlaces internos que no resuelven.

Enlaces externos: hoy la frontera los declina, correcto para navegar e insuficiente para
reportar. Un blog enlaza fuera y saber que un enlace externo está roto es útil; se **reportan**
como declinados con su URL, y comprobarlos queda como decisión del ADR — alcanza a terceros, y
eso es política, no implementación.

**Gates**
- Un barrido de un sitio de varias páginas reporta una fila por estado alcanzable.
- Una página con un 500 plantado aparece señalada.
- Un JS roto plantado aparece señalado.
- Un sitio con cien páginas equivalentes no produce cien hallazgos iguales: la normalización de
  rutas que la exploración ya hace debe sostenerlo, y el test lo fija.
- Cero llamadas al modelo en un barrido. Medido, no supuesto.

### Slice 4 — Overlays de consentimiento

**ADR 0017** primero, porque **aceptar cookies es tomar una decisión de consentimiento** y un
agente no debería tomarla implícitamente. Recomendación de partida: preferir la opción que menos
concede —en el sitio medido, «Only essentials» y no «Accept all»— y que sea elección explícita
de la policy, nunca comportamiento tácito.

1. Detección a partir de lo que la observación ya lista: `dialog` y `alertdialog` están en los
   roles interactivos y sus botones aparecen como affordances.
2. Cierre acotado, bajo la decisión de policy, registrado como acción visible en el log.

**Gates**
- Un sitio con banner deja ver el contenido detrás.
- El cierre aparece en el log: nunca una acción invisible.
- Con la policy que lo prohíbe, el run no lo cierra y lo dice.
- La opción elegida por defecto es la que menos concede.

### Slice 5 — El run cuenta lo que hizo *(R5)*

25 llamadas al modelo y otras tantas acciones dejaron **tres** eventos en el log durable. Para
depurar un run atascado, el operador se queda con el veredicto y una captura.

1. Un evento por acción: tipo, intent, resultado, url, estado HTTP.
2. Redactado antes de publicar — un `fill` lleva el valor tecleado.
3. Acotado por los presupuestos del run.

**Impacto de contrato:** tipos nuevos en `contracts/run-event.schema.json`. Confirmar que la
política de compatibilidad los admite como aditivos y que un consumidor tolera un tipo que no
conoce.

**Gates**
- El log reconstruye la secuencia de acciones.
- Ningún valor tecleado aparece sin redactar.
- CLI y frontend siguen leyendo el stream sin cambios.

### Slice 6 — Cierre

1. Ampliar el *reference story set* de Phase 15 con los arquetipos que esta fase habilita, y
   volver a medir.
2. **Un smoke contra al menos dos sitios públicos que no se usaron para desarrollar**, uno de
   ellos con banner de consentimiento.
3. `bash scripts/ci-local.sh` verde.
4. README: el producto deja de describirse contra un solo tipo de aplicación.
5. `PROGRESS.md` y `HANDOFF.md` con comandos y resultados reales.

---

## Gates de fase

- Un barrido determinista produce un reporte útil con **cero** llamadas al modelo.
- Un 404 y un 5xx se distinguen entre sí y de una página sana.
- Errores de consola y peticiones fallidas aparecen en el reporte, separados de las conclusiones
  del modelo.
- Un banner de consentimiento no impide probar el sitio, y cerrarlo nunca es invisible.
- Una exploración mapea un sitio real sin ayuda de su test.
- Nada de lo añadido introduce un `failed` que no venga de una comprobación determinista.
- Redacción verificada en las salidas nuevas: reporte, eventos, state map, grafo.
- `bash scripts/ci-local.sh` verde.

---

## Fuera de alcance

**Runs autenticados** — `plans/phase-17-authenticated-runs.md`. Un sitio detrás de login es **un
arquetipo más**, no la puerta a los demás: una landing, un blog o una documentación no necesitan
sesión, y son exactamente los casos que esta fase habilita.

**Rendimiento, accesibilidad y responsive como veredictos.** Un barrido determinista invita a
añadirlos y cada uno es una fase con su propio vocabulario de hallazgos. Nota para quien la
escriba: los 23 segundos de `load` que la slice 2 de Phase 15 midió son un hallazgo de
rendimiento que esas fases deliberadamente sólo *toleran*.
