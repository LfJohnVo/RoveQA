# Inference Layer

## Port
El agente usa `ModelRouter.infer(task_type, context, constraints)`; nunca provider-specific calls fuera de infrastructure.

Implementado (Phase 06):
- `domain/inference/tasks.py`: `TaskType`, `ModelCapability`, `InferenceBudget`. El Domain nombra capability, no modelos.
- `infrastructure/inference/router.py`: `ModelRouter` indexa endpoints por capability. Una task sin endpoint falla con `NoEndpointConfiguredError`; nunca se degrada `DEEP` al modelo fast.
- `infrastructure/inference/vllm/gateway.py`: `VLLMModelGateway` implementa el port `ModelGateway` que ya consumía el graph. La forma del workflow no cambia (ADR 0009).

Una decisión no obtenida se reporta como `PlannedAction(failure=...)`, no como excepción ni como
`action=None`. Una excepción haría que Temporal reintentara el episodio como fallo de
infraestructura; un `action=None` vacío se leería como "objetivo cumplido" y el run pasaría.

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

`response_format: json_schema` con guided decoding (`--guided-decoding-backend`) restringe la
generación en el servidor; la validación Pydantic se ejecuta igual del lado del cliente, porque un
servidor que ignore el campo o una completion truncada deben fallar cerrado.

`side_effect` no se cree al modelo cuando baja el nivel de seguridad: toda acción fuera de
`READ_ONLY_ACTIONS` se trata como state-changing aunque el modelo diga lo contrario. El flag sólo
sirve para escalar (una navegación que confirma algo). Un modelo persuadido por contenido de página
puede proponer mal una acción legal, nunca una ilegal.

### Límites y fallos
- Concurrencia por endpoint con `ResourceSemaphore` en Redis: el límite pertenece al servidor, así
  que dos workers comparten el mismo presupuesto. Saturación sostenida → `ModelUnavailableError`.
- Retries sólo de transporte (timeout, connection error, 5xx) y acotados por `InferenceBudget`.
  Un 4xx no se reintenta. Los retries semánticos son del nodo Recover (ADR 0009).
- Circuit breaker por endpoint: tras N fallos de transporte consecutivos las llamadas fallan rápido
  durante un cooldown. Output inválido no abre el circuito — el endpoint está respondiendo.
- Métricas por endpoint: latencia, tokens, errores y `invalid_outputs` (contado aparte). Nunca se
  registran prompts ni completions.

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
