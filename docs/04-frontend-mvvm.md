# Frontend — Clean Architecture + MVVM

## Direction

```text
View -> ViewModel -> Application -> Domain
                         ^
                         |
                  Infrastructure adapters
```

## Proposed tree

```text
frontend/src/
├── domain/
│   ├── runs/
│   ├── projects/
│   ├── findings/
│   └── browser/
├── application/
│   ├── usecases/
│   └── ports/
├── infrastructure/
│   ├── api/
│   └── realtime/
├── viewmodels/
│   ├── runs/
│   ├── projects/
│   └── knowledge/
└── views/
    ├── pages/
    └── components/
```

## State ownership
- TanStack Query: server state durable/remote.
- WebSocket adapter: realtime events; normaliza y entrega al application layer/ViewModel.
- Zustand: UI state compartido que no pertenezca al servidor.
- Local component state: detalles puramente visuales locales.
- React Hook Form + Zod: forms.

## Example RunViewModel surface
`status`, `currentGoal`, `currentUrl`, `stepCount`, `findings`, `isConnected`, `pause()`, `resume()`, `cancel()`, `selectStep(id)`.

La View no conoce endpoints ni event names de transporte.
