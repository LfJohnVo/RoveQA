---
name: frontend-design
description: Diseña e implementa interfaces frontend distintivas y production-grade en React cuando el trabajo implique composición visual, styling, componentes, páginas o polish. Usar junto con interface-design para producto UI y respetar siempre MVVM/Clean Architecture.
---
# Frontend design

Aplicar esta skill cuando el scope requiera calidad visual real, no sólo funcionalidad.

## Workflow
1. Leer primero el contexto de producto, `docs/04-frontend-mvvm.md` y cualquier `.interface-design/system.md` existente.
2. Definir una dirección visual explícita antes de escribir JSX/CSS: densidad, jerarquía, tipografía, superficies, contraste y movimiento.
3. Reutilizar tokens y patrones existentes. No inventar una segunda estética en una pantalla aislada.
4. Implementar componentes reales, responsivos, accesibles y con todos sus estados.
5. Mantener la View presentacional: no meter fetch, WebSocket ni reglas de negocio en componentes.
6. Verificar keyboard navigation, focus visible, contraste, reducción de movimiento y tamaños interactivos.
7. Ejecutar lint, type-check, tests y build del frontend.

## Quality bar
- Evitar el aspecto genérico de UI generada: card soup, gradientes decorativos sin intención, exceso de pills, sombras arbitrarias y spacing inconsistente.
- Usar jerarquía clara: una acción primaria por contexto, secundarios visibles pero subordinados.
- Hacer que tablas, timelines, logs y estados densos sigan siendo legibles.
- Preferir motion funcional: cambio de estado, aparición contextual y orientación espacial; no animación ornamental constante.
- Mostrar loading, empty, error, disconnected, recovering, paused y stale cuando correspondan.
- No sacrificar performance o accesibilidad por estética.

## Project-specific emphasis
Esta aplicación es una consola operacional para runs agenticos. Priorizar legibilidad prolongada, densidad controlada, evidencia clara, estados de recuperación y observación en tiempo real sobre estética de landing page.
