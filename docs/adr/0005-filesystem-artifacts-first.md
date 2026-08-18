# Filesystem artifacts first

Status: Accepted

## Context
La plataforma debe permanecer ligera, durable y reemplazable por adapters.

## Decision
En single-node se usa filesystem para evidencia y un ArtifactRepository para permitir migración posterior a S3/MinIO.

## Consequences
La implementación y tests deben respetar esta separación. Cualquier cambio sustancial requiere un ADR superseding.
