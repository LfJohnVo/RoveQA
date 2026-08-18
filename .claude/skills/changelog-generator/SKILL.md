---
name: changelog-generator
description: Genera y mantiene changelogs/release notes a partir del historial Git y cambios reales del repositorio. Usar al preparar releases, milestones o resúmenes de cambios, siguiendo Keep a Changelog y Conventional Commits cuando estén disponibles.
---
# Changelog generator

## Workflow
1. Determinar rango: último tag..HEAD, rango indicado o commits de la fase/release.
2. Inspeccionar `git log`, PR/commit context disponible y diffs cuando el mensaje no baste.
3. Categorizar cambios relevantes en Added, Changed, Deprecated, Removed, Fixed y Security.
4. Separar breaking changes de forma explícita.
5. Traducir detalles internos a impacto comprensible sin inventar beneficios no demostrados.
6. Omitir ruido puramente interno del changelog público salvo que afecte operación, seguridad, compatibilidad o mantenimiento importante.
7. Proponer versión SemVer sólo si la evidencia permite hacerlo.
8. Actualizar `CHANGELOG.md` preservando entradas existentes y formato del repositorio.
9. Mostrar el rango y comandos utilizados para que el resultado sea auditable.

## Rules
- No afirmar que un bug quedó resuelto si el fix/tests no están en el rango.
- No inventar PR numbers, fechas, autores o métricas.
- Cambios de schema/API/behavior incompatibles deben quedar destacados.
- Seguridad puede requerir redacción responsable; no publicar secretos ni detalles explotables innecesarios.
