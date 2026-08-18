---
name: backend-slice
description: Implementa un vertical slice backend en FastAPI/Python respetando Domain, Application, Infrastructure e Interfaces, incluyendo tests y migraciones cuando corresponda. Usar para endpoints, use cases, repositories y domain behavior.
---
# Backend vertical slice $ARGUMENTS

1. Si el slice expone/cambia HTTP, aplicar `api-design-principles`; si toca errores/retries aplicar `error-handling-patterns`; si toca SQLAlchemy/Alembic/queries aplicar `postgresql`.
2. Identificar behavior, invariants y boundary inputs/outputs.
3. Crear/ajustar Domain primero sólo si existe lógica de negocio real.
4. Definir command/query y use case en Application.
5. Definir ports consumidos por Application.
6. Implementar adapters concretos en Infrastructure.
7. Exponer por Interfaces/FastAPI con DTO validation y error mapping.
8. Agregar migración sólo cuando cambie el schema durable.
9. Agregar unit tests Domain/Application e integration tests del adapter/endpoint necesario.
10. Ejecutar ruff, type-check y pytest del scope.
11. Actualizar docs/contratos si cambió API/evento/schema.
