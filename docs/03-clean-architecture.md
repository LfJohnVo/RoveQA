# Backend Clean Architecture

## Dependency rule

```text
Interfaces/Delivery ----> Application ----> Domain
Infrastructure ---------> Application ----> Domain
```

Nunca en dirección contraria.

## Proposed package

```text
backend/src/agentic_qa/
├── domain/
│   ├── projects/
│   ├── runs/
│   ├── agent/
│   ├── browser/
│   ├── qa/
│   ├── inference/
│   └── knowledge/
├── application/
│   ├── commands/
│   ├── queries/
│   ├── ports/
│   └── services/
├── infrastructure/
│   ├── persistence/postgres/
│   ├── cache/redis/
│   ├── graph/falkordb/
│   ├── browser/playwright/
│   ├── inference/vllm/
│   ├── inference/airllm/
│   ├── workflows/temporal/
│   └── artifacts/filesystem/
├── interfaces/
│   ├── http/
│   ├── websocket/
│   ├── cli/
│   └── mcp/
└── bootstrap/
```

## Ports worth defining early
- `RunRepository`
- `ProjectRepository`
- `StoryRepository`
- `CheckpointRepository`
- `EventPublisher`
- `LockManager`
- `BrowserGateway`
- `ArtifactRepository`
- `ModelGateway` / `ModelRouter`
- `KnowledgeRepository`
- `WorkflowGateway`

## Mapping discipline
ORM model != domain entity != API DTO. Mapping explícito en boundaries para evitar que cambios de infraestructura contaminen Domain.
