# Revisar antes de cerrar una fase

```text
Revisa la fase actual como release gate. Aplica architecture-guard, durability-review si toca workflows/browser/actions, ejecuta todos los tests/lint/type-check/build requeridos y contrasta cada acceptance gate del archivo plans correspondiente. Si aparece un fallo inesperado usa systematic-debugging antes de corregirlo. Sólo entonces actualiza PROGRESS.md/HANDOFF.md.
```
