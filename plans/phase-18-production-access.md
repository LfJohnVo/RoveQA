# Phase 18 — Production Access

## Objective

Que un equipo de desarrollo pueda apuntar su CI a esta plataforma y correr pruebas en cada
feature que libere, sin que eso signifique dejar el sistema abierto.

Hoy **el API no tiene autenticación**. Cualquiera que alcance el puerto 8000 puede lanzar
runs contra cualquier origen permitido, leer todos los reportes y registrar o revocar
sesiones. No es un descuido: `docs/13-security.md` reserva `AUTH_REQUIRED`/`FORBIDDEN` y el
exit code 3 para esto y dice que la auth real requiere un ADR. Todo el lado cliente ya
existe —la CLI manda `Authorization: Bearer`, el token sólo puede venir del entorno o del
config de usuario y nunca del versionado, y los códigos y el exit code están reservados—.
Falta la mitad del servidor, y es lo único que separa esto de poder salir.

Las otras tres carencias de red (sin TLS, todo publicado en `0.0.0.0`, keyring protegido
sólo por el host) se siguen de la misma decisión y se cierran aquí con ella.

## Decisión estructural

**ADR 0020 — Autenticación del API por tokens de proyecto.** Se crea antes de implementar.
Lo que tiene que cerrar, en orden de riesgo:

1. **Qué identifica un token.** Un proyecto, no una persona. El caso que esta fase existe
   para servir es el CI de un repositorio, que no es nadie y no inicia sesión. Usuarios y
   roles son otro producto encima de éste y quedan fuera.
2. **Cómo se guarda.** Nunca en claro. Un token lo genera el servidor y tiene entropía
   completa, así que el hash correcto es rápido (SHA-256) y **no** un KDF de contraseñas:
   bcrypt/argon2 existen para secretos que una persona eligió, y aquí sólo añadirían
   latencia por petición sin defender de nada. La comparación es de tiempo constante.
3. **Quién puede emitir uno.** Nadie por HTTP. Emitir se hace con un comando en el host,
   igual que el keyring de la fase 17: la frontera de confianza es la máquina. Así no
   existe una ruta que cree credenciales, no hay super-token de administración que robar,
   y no hay nada que forzar por fuerza bruta.
4. **Cómo se comprueba el alcance sin depender de la disciplina.** Cada ruta que nombra un
   proyecto —o un run, o un entorno, que pertenecen a uno— tiene que verificar que el token
   lo cubre. Una comprobación por endpoint se olvida en el endpoint número doce, así que
   hace falta que sea estructural y que un test recorra el OpenAPI y falle si aparece una
   ruta sin cubrir.
5. **Qué queda abierto.** `/health` sí, porque lo usa el healthcheck del contenedor y un
   proxy. Todo lo demás no. La lista de exenciones vive en un solo sitio y el mismo test la
   lee.
6. **Qué pasa cuando falta o no sirve.** `401` con `AUTH_REQUIRED` y `403` con `FORBIDDEN`,
   en el mismo envelope de error que ya existe, para que la CLI salga 3 sin cambios.

**ADR 0021 — Postura de red del despliegue.** Decidido con el operador: red interna, proxy
propio. Todo escucha en loopback salvo el API, cuya dirección de bind es configurable
porque el proxy puede estar en otra máquina. No entran certificados ni configuración de
proxy al repositorio: se documenta el contrato que el proxy tiene que cumplir.

## Slices

### Slice 1 — El token, y dónde vive

1. `ApiToken` en el dominio: identidad, proyecto, etiqueta, cuándo y quién lo emitió.
   Sin el valor — igual que `EnvironmentSession` no tiene dónde poner una cookie.
2. Hash y comparación de tiempo constante en el dominio, con el razonamiento de por qué
   SHA-256 y no un KDF escrito donde alguien lo va a leer.
3. Tabla `api_tokens` con índice único sobre el hash, migración, repositorio y contract
   tests sobre los dos adapters.

**Gates**
- Un token emitido dos veces nunca colisiona ni en valor ni en hash.
- El valor no aparece en ninguna columna de la base.
- Buscar por hash es una búsqueda indexada, no un recorrido.

### Slice 2 — Emitir, listar y revocar desde el host

1. `python -m agentic_qa.admin token issue|list|revoke`, dentro del contenedor del API.
2. El valor se imprime **una sola vez** y no vuelve a existir en ninguna parte.
3. Revocar borra la fila o la marca; a diferencia de una sesión, aquí no hay clave fuera
   de la base, así que la decisión se toma y se justifica en el ADR.

**Gates**
- No existe ninguna ruta HTTP que emita un token; un test lo asevera contra el OpenAPI.
- Emitir dos veces para el mismo proyecto da dos tokens independientes y revocar uno deja
   vivo al otro.

### Slice 3 — La comprobación, y que no se pueda olvidar

1. Dependencia que autentica (`401` sin token o con uno desconocido) y autoriza (`403` si
   el token no cubre el recurso).
2. Resolución del proyecto del recurso desde la ruta: `project_id` directo, `run_id` y
   `environment_id` por su fila.
3. Test estructural: recorre las rutas del OpenAPI y falla si alguna no está cubierta ni
   exenta. Con una ruta plantada para probar que el test muerde.
4. La CLI sale 3 contra un servidor que pide auth, con el mensaje que dice qué hacer.

**Gates**
- Un token del proyecto A recibe `403` en cada ruta del proyecto B.
- Añadir una ruta sin cubrirla rompe el suite.
- `/health` sigue abierta y el healthcheck del contenedor sigue verde.

### Slice 4 — Postura de red

1. Todo a loopback en `compose.yaml` salvo el API, con la dirección del API configurable.
2. `.env.example` y README con el contrato que el proxy tiene que cumplir.
3. Un test de `compose config` que falle si un servicio vuelve a publicarse en `0.0.0.0`.

**Gates**
- `docker compose config` no expone PostgreSQL, Redis, Temporal, FalkorDB ni vLLM fuera de
  loopback.
- El stack sigue arrancando y el smoke sigue pasando.

### Slice 5 — El camino que el equipo va a recorrer

1. Un ejemplo de workflow —GitHub Actions y GitLab CI— que arranca un run por push y
   publica el resultado como JUnit con el exportador que ya existe.
2. Documentación de un solo sitio: emitir el token, guardarlo como secreto del repositorio,
   apuntar la CLI, leer el exit code.
3. Un ensayo de verdad: token nuevo, run desde un contenedor limpio con sólo ese token,
   reporte leído, token revocado, y el siguiente intento sale 3.

**Gates**
- Un CI con sólo el token y la URL completa el ciclo sin más configuración.
- Revocar corta al CI en la petición siguiente.

### Slice 6 — Cierre

1. `bash scripts/ci-local.sh` verde.
2. `PROGRESS.md`, `HANDOFF.md` y `CONTINUE_HERE.md` con comandos y resultados reales.
3. La sección «¿Se puede liberar a producción?» reescrita con lo que quede cierto.

## Gates de fase

- Ninguna ruta salvo las exentas responde sin un token válido.
- Un token no alcanza los recursos de otro proyecto.
- Ningún token existe en claro fuera del momento en que se emite.
- Emitir requiere acceso al host; no hay ruta HTTP que lo haga.
- Nada salvo el API escucha fuera de loopback.
- Un CI ajeno completa el ciclo con un token y la URL, y revocar lo corta.
- `bash scripts/ci-local.sh` verde.

## Fuera de alcance

- Usuarios, roles y gestión de cuentas. Otro producto; requiere decidir proveedor de
  identidad y no hace falta para que un CI corra pruebas.
- Terminación TLS dentro del stack. El operador tiene proxy propio; meter certificados
  aquí sería configuración de su infraestructura viviendo en este repositorio.
- Rotación automática de tokens y caducidad. Se emiten y se revocan a mano, que es lo que
  un equipo necesita el primer año; una caducidad que nadie renueva es un CI roto un
  martes por la mañana.
- Cuotas y límites por token. No hay evidencia todavía de que hagan falta, y el
  `RunPolicy` ya acota lo que un run puede gastar.
