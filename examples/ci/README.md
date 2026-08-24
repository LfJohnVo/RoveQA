# Running RoveQA from CI

Tres ficheros y una regla.

- `github-actions.yml` y `gitlab-ci.yml` — el mismo pipeline en las dos formas:
  instalar, `doctor`, `plan lint`, `run create`, `run wait`, y recoger la evidencia si
  no pasó.
- `verdict-to-junit.mjs` — traduce el envelope a JUnit **sin decidir el resultado**. Vive
  en el paquete de la CLI (`cli/examples/`) y se instala con ella: quien hace
  `npm install -g` obtiene el adaptador, en vez de que le digan que copie un fichero de
  un repositorio que no tiene.

## Lo primero: el token

Tres variables en el CI, y sólo una es un secreto:

| Variable | Qué es |
| --- | --- |
| `ROVEQA_API_URL` | dónde está el API, a través de tu proxy |
| `ROVEQA_PROJECT_ID` | el proyecto que este repositorio prueba |
| `ROVEQA_TOKEN` | el secreto, emitido en el host de RoveQA |

Se emite una vez, en la máquina, y se muestra una vez:

```bash
docker compose exec api python -m agentic_qa.admin token issue     --project <id> --label "github actions"
```

No hay endpoint que emita tokens y no lo habrá: emitir una credencial es un acto del
host, y trazar ahí la frontera significa que no hay ruta que filtrar, ninguna que forzar,
y ningún token de administración cuyo robo escale de un proyecto a todos (ADR 0020).

**Un token alcanza su proyecto y ninguno más.** El pipeline de un repositorio no puede
tocar la aplicación de otro equipo, y revocar el token de uno no corta a los demás:

```bash
docker compose exec api python -m agentic_qa.admin token list   --project <id>
docker compose exec api python -m agentic_qa.admin token revoke <token-id>
```

Si se pierde el valor, se emite otro y se revoca éste. No hay forma de recuperarlo, y esa
es la única recuperación honesta de un secreto que nadie guardó.

`ROVEQA_TOKEN` y no una bandera: un token en la línea de comandos acaba en el historial
del shell y en el log del propio job.

**La regla:** el adaptador sale con el código que le dio la CLI. Un adaptador que
reportara "los tests corrieron" mientras el run se quedó sin tiempo sería peor que no
tener adaptador — convertiría en verde una pregunta que nadie respondió.

Los tres desenlaces son distintos y el reporte los distingue:

| Salida | Qué significa | En el JUnit |
| --- | --- | --- |
| 0 | verdict `passed` | un testcase sin fallos |
| 1 | verdict terminal que no es pass (`failed`, `blocked`, `inconclusive`) | `<failure>` con el verdict |
| 3 | el token falta, no vale, o no alcanza ese proyecto | el job falla antes de arrancar nada |
| 7 | la espera del cliente venció; **el run sigue vivo** | `<error>` con cómo retomar |

Un `blocked` no es un defecto: el run no pudo hacer su trabajo y dice por qué
(`policy`, `agent_budget`, `model`). Tratarlo como un fallo de producto es cómo un
reporte pierde su credibilidad.
