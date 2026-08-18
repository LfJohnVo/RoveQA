---
name: interface-design
description: Diseña y mantiene el sistema de interfaz de producto para dashboards, herramientas, paneles administrativos y superficies operacionales. Usar al crear o revisar layout, jerarquía, estados, tokens, navegación, tablas, timelines, forms o consistencia visual.
---
# Interface design

Usar para product UI. No reemplaza `frontend-design`: esta skill fija el sistema; `frontend-design` eleva la ejecución visual.

## Persistent design memory
- Antes de diseñar, buscar `.interface-design/system.md`.
- Si no existe al comenzar la fase de frontend, crearla usando `templates/INTERFACE_SYSTEM_TEMPLATE.md`.
- Actualizarla sólo cuando una decisión sea verdaderamente reusable.
- No cambiar tokens globales silenciosamente para resolver un componente local.

## Decide explicitly
Para cada nueva superficie definir:
- information hierarchy y primary task;
- layout grid y density;
- spacing scale;
- typography scale;
- radii/borders/elevation strategy;
- semantic colors y status vocabulary;
- interaction states;
- responsive behavior;
- keyboard/focus behavior;
- realtime/disconnected/recovery states.

## Product rules
- Mostrar estado del sistema antes que decoración.
- Separar status, progress, findings, evidence y controls visualmente.
- No depender sólo de color para severity/status.
- Mantener acciones destructivas claramente separadas y confirmables.
- Formularios: labels persistentes, errores junto al campo y summary cuando sea útil.
- Data-heavy UI: sticky headers/columns sólo cuando mejoren orientación; virtualizar listas largas cuando esté justificado.
- Timeline/event stream: distinguir tiempo, actor, intent, action, result y evidence sin convertir todo en texto monoespaciado.

## Architecture constraint
Las decisiones de UI terminan en Views/ViewModels; nunca introducir acceso directo a infraestructura para resolver un problema visual.
