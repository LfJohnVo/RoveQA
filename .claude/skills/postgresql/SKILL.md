---
name: postgresql
description: "Diseña, implementa y revisa PostgreSQL para la verdad durable del proyecto: schemas, constraints, migrations, transactions, indexes, queries, concurrency, checkpoints y recuperación. Usar en cambios SQLAlchemy/Alembic o problemas de rendimiento/integridad."
---
# PostgreSQL

PostgreSQL es durable truth de metadata, runs y checkpoints persistentes. Redis no sustituye constraints ni integridad durable.

## Schema design
- Modelar relaciones importantes relacionalmente; usar JSONB para payloads evolutivos, no como escape de diseño.
- Usar `timestamptz` y tratar timestamps de forma consistente.
- Declarar `NOT NULL`, foreign keys, unique constraints y checks para invariants que DB pueda defender.
- No duplicar datos derivados sin estrategia de consistencia.
- Separar blobs/artifacts grandes: guardar referencias, no screenshots/videos en tablas operacionales.

## Migrations
- Cada cambio durable pasa por Alembic.
- Mantener migraciones pequeñas, reproducibles y revisables.
- Para cambios online riesgosos, preferir expand -> backfill -> switch -> contract.
- Verificar upgrade desde DB vacía y, cuando sea razonable, downgrade de la migración nueva.
- Nunca editar una migración ya desplegada para ocultar un cambio posterior.

## Queries and indexes
- Diseñar índices desde queries reales: filters, joins, ordering y uniqueness.
- No crear índices redundantes "por si acaso".
- Para queries lentas usar `EXPLAIN (ANALYZE, BUFFERS)` en un entorno seguro/representativo.
- Evitar N+1 y cargas completas cuando basta projection/pagination.

## Transactions and concurrency
- Mantener transacciones cortas; no sostenerlas durante calls a modelos/browser/red.
- Usar DB constraints como última defensa contra duplicados.
- Elegir locking/isolation conscientemente para transitions críticas.
- Side effects externos no son atómicos con PostgreSQL: aplicar outbox/idempotency/verify-before-retry cuando el flujo lo necesite.

## Operations
- Configurar pool y timeouts explícitos.
- Instrumentar slow queries, pool exhaustion y deadlocks.
- Mantener procedimiento probado de backup/restore antes de release candidate.
