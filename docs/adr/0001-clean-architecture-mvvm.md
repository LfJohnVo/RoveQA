# Clean Architecture + MVVM

Status: Accepted

## Context
La plataforma debe permanecer ligera, durable y reemplazable por adapters.

## Decision
Backend usa Clean Architecture; frontend usa Clean Architecture con MVVM. Se evita acoplar dominio y presentación a frameworks para permitir cambios de infraestructura y testing aislado.

## Consequences
La implementación y tests deben respetar esta separación. Cualquier cambio sustancial requiere un ADR superseding.
