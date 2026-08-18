---
paths:
  - "frontend/src/**/*.{ts,tsx}"
---
# Frontend MVVM rules
- Views sólo renderizan y envían intents al ViewModel.
- ViewModels no importan componentes React de presentación.
- Use cases no dependen de React.
- HTTP/WebSocket viven en infrastructure.
- TanStack Query maneja server state; Zustand sólo UI/ViewModel state que lo necesite.
- Validación de forms con Zod/React Hook Form; no duplicar reglas arbitrariamente en componentes.
