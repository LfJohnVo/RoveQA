---
paths:
  - "backend/**/*.py"
---
# Backend rules
- Mantener `domain -> application -> infrastructure/interfaces` como dirección de dependencias.
- Preferir Protocol/ABC ports definidos cerca de la capa que los consume.
- No filtrar modelos ORM fuera de infrastructure.
- Usar DTOs/commands explícitos en boundaries.
- I/O externo siempre async cuando la librería lo permita.
- Errores de dominio no deben depender de HTTP status codes.
