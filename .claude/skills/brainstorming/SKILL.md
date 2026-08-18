---
name: brainstorming
description: Explora y cierra decisiones antes de implementar una capacidad, UX flow o cambio estructural ambiguo. Usar cuando haya varias soluciones razonables o requisitos incompletos; no reabrir ADRs/fases ya decididas ni usar para un bug reproducible.
---
# Brainstorming

Objetivo: convertir ambigüedad en una decisión implementable antes de escribir código.

## Workflow
1. Leer el código, ADRs, plan de fase y docs relevantes antes de preguntar.
2. Identificar exactamente qué decisión sigue abierta. No volver a cuestionar decisiones ya fijadas por el usuario o un ADR aceptado.
3. Si hace falta interacción, hacer una pregunta de alto valor a la vez.
4. Proponer 2-3 alternativas reales con tradeoffs de complejidad, durabilidad, seguridad, performance y mantenimiento.
5. Recomendar una opción coherente con la arquitectura existente.
6. Capturar la decisión:
   - ADR si es estructural;
   - actualización de spec/plan si cambia comportamiento;
   - `.interface-design/system.md` si es una regla reusable de interfaz.
7. Convertir la decisión en acceptance criteria y slices pequeños.
8. Sólo entonces pasar a implementación.

## Do not overuse
- Si `/implement-phase` ya contiene una decisión explícita, ejecutarla.
- Si existe un bug/test failure, usar `systematic-debugging`.
- Si la elección es local, reversible y no cambia contratos, elegir la opción más simple coherente y documentar brevemente si es necesario.
