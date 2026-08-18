---
name: frontend-mvvm-slice
description: Implementa un vertical slice React/Vite usando Clean Architecture + MVVM, separando View, ViewModel, application use cases, domain e infrastructure. Usar para pantallas, realtime dashboards, forms y controles de runs.
---
# Frontend MVVM slice $ARGUMENTS

1. Para una nueva superficie/product UI aplicar `interface-design` + `frontend-design`; para cualquier React aplicar `vercel-react-best-practices`.
2. Definir comportamiento observable de la pantalla y estados: loading, empty, success, error, realtime/disconnected si aplica.
3. Modelar entidades/value objects y repository ports si no existen.
4. Implementar use cases independientes de React.
5. Implementar adapters HTTP/WebSocket en infrastructure.
6. Implementar ViewModel como hook/store con state derivado y commands claros.
7. Implementar View sin acceso directo a HTTP/WebSocket.
8. Server state con TanStack Query; UI-only state con Zustand sólo cuando aporte valor.
9. Tests: use cases, ViewModel behavior y componentes críticos.
10. Ejecutar lint, type-check, tests y build.
