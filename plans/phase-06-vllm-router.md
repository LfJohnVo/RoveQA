# Phase 06 — vLLM + Model Router

## Objective
Integrar inferencia real tras un port estable y structured outputs validados.

## Tasks
1. ModelRouter policy y task types.
2. OpenAI-compatible vLLM adapter.
3. Pydantic schemas para BrowserDecision/Plan/Extraction.
4. Timeout/retry/circuit behavior.
5. Redis semaphore por model endpoint.
6. Metrics de latency/tokens/errors.
7. Fallback a deterministic failure/replan, no acciones ambiguas.

## Gates
- Invalid model output no llega a Playwright.
- Concurrency limit demostrado.
- Agent system test con modelo real opcional y fake model obligatorio en CI.
## Required skills
- `prompt-engineering-patterns`
- `error-handling-patterns`
- `durability-review` for inference activities that participate in durable runs



## Future boundary
No implementar Graphiti memory aquí. Sin embargo, mantener el ModelRouter extensible para que Phase 09 pueda añadir `EmbeddingGateway`/pooling inference sin acoplar Domain a vLLM.
