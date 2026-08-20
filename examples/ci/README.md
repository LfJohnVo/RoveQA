# Running RoveQA from CI

Dos ficheros y una regla.

- `github-actions.yml` — el workflow: instalar, `doctor`, `plan lint`, `run create`,
  `run wait`, y recoger la evidencia si no pasó.
- `verdict-to-junit.mjs` — traduce el envelope a JUnit **sin decidir el resultado**. Vive
  en el paquete de la CLI (`cli/examples/`) y se instala con ella: quien hace
  `npm install -g` obtiene el adaptador, en vez de que le digan que copie un fichero de
  un repositorio que no tiene.

**La regla:** el adaptador sale con el código que le dio la CLI. Un adaptador que
reportara "los tests corrieron" mientras el run se quedó sin tiempo sería peor que no
tener adaptador — convertiría en verde una pregunta que nadie respondió.

Los tres desenlaces son distintos y el reporte los distingue:

| Salida | Qué significa | En el JUnit |
| --- | --- | --- |
| 0 | verdict `passed` | un testcase sin fallos |
| 1 | verdict terminal que no es pass (`failed`, `blocked`, `inconclusive`) | `<failure>` con el verdict |
| 7 | la espera del cliente venció; **el run sigue vivo** | `<error>` con cómo retomar |

Un `blocked` no es un defecto: el run no pudo hacer su trabajo y dice por qué
(`policy`, `agent_budget`, `model`). Tratarlo como un fallo de producto es cómo un
reporte pierde su credibilidad.
