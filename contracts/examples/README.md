# Contract examples

Un ejemplo canónico por contrato público. Existen para que un consumidor externo tenga
contra qué comparar sin leer el código de nadie, y para que un cambio incompatible rompa
un gate aquí en vez de romper a alguien allá fuera.

Los identificadores son deliberadamente estables y evidentemente falsos
(`00000000-0000-4000-8000-...`). Cada fichero se validó contra su schema al escribirlo, y
`cli/test/contract-examples.test.ts` los vuelve a validar en cada corrida: un ejemplo que
dejó de cumplir su propio schema es peor que no tener ejemplo, porque alguien lo copiaría.

| Fichero | Schema | Qué muestra |
| --- | --- | --- |
| `test-plan.example.json` | `test-plan.schema.json` | Un plan con una acción y una aserción anclada a un criterio |
| `cli-envelope.success.example.json` | `cli-envelope.schema.json` | La respuesta de `run wait` con un verdict terminal |
| `cli-envelope.error.example.json` | `cli-envelope.schema.json` | Un timeout de espera: el run sigue vivo y el envelope dice cómo retomar |
| `failure-bundle.manifest.example.json` | `failure-bundle.schema.json` | El manifest de un fallo con su evidencia y una hipótesis etiquetada |

## Política de compatibilidad

Los tres contratos llevan `schema_version` con un `const`. Un cambio **aditivo** —un campo
opcional nuevo— no cambia la versión. Un cambio que un consumidor v1 no pueda leer exige
una versión nueva y un periodo en el que el servidor hable las dos; no hay forma de
"actualizar en silencio" un contrato que otra gente ya está parseando.
