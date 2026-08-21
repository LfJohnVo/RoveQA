# Phase 17 — Authenticated Runs

## Objective

Que un run pueda probar la parte de una aplicación que está detrás del login. Hoy no
existe ningún concepto de credencial: `storage_state` está cableado sólo para *recovery* y
`browser_factory` abre siempre un contexto anónimo.

**Un sitio con login es un arquetipo más, no la puerta a los demás.** Una landing, un blog,
una documentación o una tienda con compra de invitado no necesitan sesión, y son los casos
que Phase 16 habilita. Esta fase va última a propósito: es el arquetipo más caro
—credenciales durables, redacción verificada, alcance de policy con sesión válida— y el que
menos generalidad añade por unidad de trabajo. El contexto anónimo sigue siendo un camino de
primera clase después de esta fase, no un caso degradado.

Depende de Phase 15 y 16. Un agente que aún no verifica de forma fiable lo que ve en abierto
no gana nada por poder entrar; y la contención de secretos que esta fase necesita se endurece
en la slice 5 de Phase 15, cuando el texto de la página entra al prompt.

## Decisión estructural

**ADR 0018 — Provisión de sesión y contención de secretos.** Se crea antes de implementar.
Las preguntas que tiene que cerrar, en orden de riesgo:

1. **Qué se guarda.** Una sesión ya establecida (`storage_state`) o una credencial con la
   que el agente hace login. Son decisiones distintas: la primera no pone nunca una
   contraseña en el bucle del agente; la segunda permite probar el login como historia.
   Recomendación de partida: soportar la primera y tratar la segunda como un caso
   explícito y acotado, no como el camino por defecto.
2. **Dónde vive.** PostgreSQL es la verdad durable del proyecto, y una credencial en claro
   en una tabla contradice `CLAUDE.md`. Cifrado en reposo con la clave fuera de la base.
3. **Qué ve el agente.** Un secreto no puede llegar al prompt, al log, al artifact, al
   state map ni al grafo. El `fill` de una contraseña tiene que poder referenciar un
   secreto sin transportarlo.
4. **Qué puede hacer un run con sesión válida.** Una sesión autenticada amplía lo
   alcanzable mucho más que un `destructive_actions: true`: la policy tiene que poder
   acotar el alcance dentro de la aplicación, no sólo el origen.
5. **Expiración e invalidación.** Una sesión caducada debe salir `blocked` con causa, nunca
   `failed`: no es un defecto del producto.
6. **Revocación que sobrevive a un restore.** Los gates de esta fase exigen que un restore
   desde backup no resucite una credencial revocada, y cifrado más validez temporal no lo
   consiguen: si la revocación vive *junto* a la credencial restaurable, restaurar un
   backup anterior devuelve el `storage_state` portador. Hace falta un mecanismo no
   restaurable — tombstone, epoch o versión de clave fuera del respaldo — y el test tiene
   que ser revocar, restaurar, y comprobar que sigue revocada.

## Tasks

1. Modelo de dominio para sesión de entorno, con provenance y validez temporal.
2. Persistencia cifrada y la operación para cargarla sin exponer el valor.
3. `browser_factory` provisiona `storage_state` por entorno; el contexto anónimo pasa a ser
   un caso, no el único.
4. Referencia a secreto en las acciones tipadas: el dominio transporta el identificador,
   la infraestructura resuelve el valor en el borde de Playwright.
5. Redacción en toda salida: prompt, eventos, artifacts, state map, grafo.
6. Detección de sesión inválida y su `failure_kind`.
7. Alcance de policy dentro de la aplicación.
8. CLI y UI para registrar y rotar una sesión sin pegarla en un fixture.

## Gates

- Una historia que sólo es alcanzable con sesión llega a `passed`.
- Ningún secreto aparece en prompt, log, evento, artifact, state map ni grafo — el test
  planta uno y lo busca en todas las salidas.
- Una sesión expirada sale `blocked` con causa; nunca `failed`.
- Rotar una credencial no exige tocar el repositorio ni reiniciar el stack.
- Un run con sesión respeta el alcance de su policy dentro de la aplicación.
- Restore desde backup no resucita una credencial revocada.
- `bash scripts/ci-local.sh` verde.
