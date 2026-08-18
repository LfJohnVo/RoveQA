# Inference Layer

## Port
El agente usa `ModelRouter.infer(task_type, context, constraints)`; nunca provider-specific calls fuera de infrastructure.

## Task types
- `GUI_ACTION`: VLM/LLM rápido, structured output.
- `STRUCTURED_EXTRACTION`: fast model.
- `SHORT_PLANNING`: fast reasoning.
- `SEMANTIC_VERIFICATION`: fast/medium.
- `DEEP_PLAN`: AirLLM candidate.
- `RUN_CRITIQUE`: AirLLM candidate.
- `ROOT_CAUSE_ANALYSIS`: AirLLM candidate.
- `FAILURE_CLUSTER_SUMMARY`: AirLLM optional, sólo después de deterministic triage.
- `MEMORY_CONSOLIDATION`: medium/deep depending size.
- `MEMORY_ENTITY_EXTRACTION`: structured output para candidates complejos.
- `EMBEDDING`: pooling model local, sin generación.

## vLLM
OpenAI-compatible adapter, structured outputs/tool-call schemas. Optimizar para throughput y repeated short decisions.

Para memory retrieval, usar un **servicio vLLM de pooling/embeddings separado** cuando sea necesario. `EmbeddingGateway` consume `/v1/embeddings`; no asumir que el mismo model server de GUI puede servir generación y embedding simultáneamente.

## AirLLM
Cold/deep path. No usar para cada click. Trigger por episode boundary, repeated failure, complex story analysis o manual deep analysis.

## Deterministic-before-semantic triage
Antes de pedir a un modelo grande que explique 100 failures:
1. Agrupar por señales deterministas/estructurales conocidas.
2. Detectar cascadas de setup/auth/dependency.
3. Elegir representative evidence.
4. Sólo después pedir semantic/root-cause analysis si aporta valor.

Esto reduce tokens/model time y evita contar 30 downstream failures como 30 defects independientes.

## Graphiti inference boundary
Graphiti soporta clients inyectables. El adapter RoveQA debe proporcionar explícitamente LLM/embedder/cross-encoder cuando aplique y pasar por nuestras policies/gateways; no usar silenciosamente los defaults de OpenAI. Structured-output ingestion debe tener evals con el modelo local seleccionado.

## Model policy
Configurable por environment/project. Domain no contiene nombres concretos de modelos; sólo capability/task types.

## Evidence boundary
Model input recibe referencias/fragmentos deliberadamente seleccionados y bounded. Model output conserva `model_invocation_id`, prompt/model version y etiqueta `model_derived=true`; nunca sobrescribe deterministic observations.
