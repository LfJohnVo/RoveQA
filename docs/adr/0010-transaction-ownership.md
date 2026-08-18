# ADR 0010 — Transaction ownership: commands own a UnitOfWork, queries take repositories

Status: Accepted

## Context
Phase 01 dejó los use cases sin `commit`: el caller era dueño del transaction boundary. Funcionaba porque ninguna operación era multi-repo atómica. Phase 02 rompe esa premisa: crear un run debe persistir **el run y su idempotency record en la misma transacción**, y debe commitear **antes** de arrancar el workflow de Temporal. Ese punto de commit es parte del contrato de durabilidad del use case, no un detalle del adapter HTTP.

Dejarlo en el delivery layer significaría poner lógica de durabilidad en Interfaces (prohibido por CLAUDE.md) y obligaría a cada endpoint a recordar si debe commitear.

La alternativa de mezclar convenciones (algunos use cases con UoW, otros con ports sueltos) deja al implementador adivinando quién commitea en cada caso.

## Decision
- **Commands (escrituras) reciben un `UnitOfWork` y son dueños de su commit.** El use case decide qué es atómico y en qué punto se hace durable.
- **Queries (lecturas) reciben el repository concreto.** No necesitan transaction semantics y exigir un UoW sólo añade ruido.
- Los repositories se obtienen **a través** del UoW (`uow.runs`, `uow.projects`), nunca inyectados en paralelo: eso hace imposible mezclar repositories de transacciones distintas.
- Salir del bloque sin `commit()` hace rollback. Olvidar el commit pierde la escritura; nunca persiste la mitad.
- El delivery layer (FastAPI, Phase 02) construye el UoW y llama al use case. No commitea ni decide atomicidad.

## Orden obligatorio para side effects externos
Persistir y commitear **primero**, disparar el efecto externo **después**:

```text
POST /runs -> [tx: run + idempotency record] -> COMMIT -> start workflow
```

Si el arranque del workflow falla, el run queda persistido en `CREATED` y es recuperable/reintentable. El orden inverso podría dejar un workflow huérfano sin fila durable, que es exactamente lo que ADR 0009 y `docs/05` prohíben.

## Consequences
- `create_project`, `create_story` y `create_run_draft` reciben `UnitOfWork`; `get_project` sigue recibiendo `ProjectRepository`.
- El fake in-memory de UoW implementa rollback real, así que un use case que olvide commitear falla también contra fakes.
- Cuando un command necesite coordinar más de un aggregate, el UoW ya es el sitio donde eso es atómico por construcción.
- Cambiar esta convención requiere un ADR superseding.
