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

## Deep endpoint (Phase 11)
Cold path. Nunca en el loop por acción: un modelo que responde en minutos detrás del planner
haría que cada browser step esperara un análisis.

- `infrastructure/inference/airllm/gateway.py`: `AirLLMDeepAnalyst` implementa el port
  `DeepAnalyst`. Habla el mismo protocolo OpenAI-compatible que el fast endpoint y reutiliza
  `VLLMChatClient`, así que admission control, timeouts, circuit breaker y validación de
  structured output son los mismos; lo que cambia es configuración.
- Configuración: `DEEP_BASE_URL` / `DEEP_MODEL` (`DEEP_TIMEOUT_SECONDS` en minutos,
  `DEEP_MAX_OUTPUT_TOKENS`). `max_concurrency=1` y `max_attempts=1`: reintentar por transporte
  una llamada que cuesta minutos duplica la espera de un endpoint que ya demostró no responder.
- El lease del slot se deriva del timeout del endpoint (`MIN_SLOT_TTL_SECONDS`,
  `SLOT_TTL_MARGIN`). Una constante fija de 120s expiraría a mitad de una llamada deep y
  entregaría el slot a otra, poniendo dos requests en una caja dimensionada para una.
- `DEEP_BASE_URL` vacío = sin análisis deep. El triage sigue agrupando y los clusters se
  almacenan igual, cada uno sin hipótesis. Ese es un reporte completo, no uno degradado.
- Cualquier servidor OpenAI-compatible sirve: `vllm-deep` (profile `deep-gpu`) con un modelo más
  grande, o un shim de AirLLM para un modelo mucho mayor que la tarjeta, capa por capa.

## Deterministic-before-semantic triage
Antes de pedir a un modelo grande que explique 100 failures:
1. Agrupar por señales deterministas/estructurales conocidas.
2. Detectar cascadas de setup/auth/dependency.
3. Elegir representative evidence.
4. Sólo después pedir semantic/root-cause analysis si aporta valor.

Implementado (Phase 11):
- `domain/triage/signals.py`: reduce un `CriterionResult` fallido a señales comparables (kind,
  criterion, HTTP status, route, fingerprint, observación normalizada). Un juicio `model_derived`
  nunca es señal de agrupación — agrupar sobre una opinión produce grupos que nadie puede
  defender después.
- `domain/triage/clustering.py`: agrupa por clave exacta y marca `blocked_downstream` lo que
  falló después de un fallo de setup en el mismo run. `AGENT_BUDGET` queda excluido de los
  setup kinds: quedarse sin acciones es consecuencia, no causa.
- `application/services/deep_analysis.py`: decide qué merece un modelo. Sólo clusters
  independientes, acotados a `DEFAULT_MAX_ANALYZED`, y sólo si `worth_asking` lo aprueba.
- `application/commands/analyze_failures.py`: el pass de frontera de run. Lee, agrupa,
  **commitea los clusters**, y sólo entonces llama al modelo — fuera de toda transacción, porque
  sostener una transacción durante minutos de inferencia está prohibido por `.claude/rules`.
  Un `IdempotencyRecord` por run evita que un retry vuelva a pagar la inferencia.
- Regla de frescura (`GROWTH_FACTOR_TO_REASK`): se vuelve a preguntar por un cluster nuevo, por
  uno que nunca se pudo explicar, o por uno que dobló de tamaño. Cada run termina disparando un
  pass, así que sin esta regla un proyecto con un muro estable compraría la misma explicación
  una vez por run.
- La hipótesis viaja **al lado** de la evidencia, nunca dentro: `AnalyzedCluster` y las tablas
  `failure_clusters` / `cluster_hypotheses` mantienen la separación estructural.
- `ClusterAnalysisRequest` no tiene dónde poner evidence refs ni artifacts: por construcción, el
  prompt no puede crecer con la cantidad de videos y traces del cluster.

Esto reduce tokens/model time y evita contar 30 downstream failures como 30 defects independientes.

## Graphiti inference boundary
Graphiti soporta clients inyectables. El adapter RoveQA debe proporcionar explícitamente LLM/embedder/cross-encoder cuando aplique y pasar por nuestras policies/gateways; no usar silenciosamente los defaults de OpenAI. Structured-output ingestion debe tener evals con el modelo local seleccionado.

## Model policy
Configurable por environment/project. Domain no contiene nombres concretos de modelos; sólo capability/task types.

## Evidence boundary
Model input recibe referencias/fragmentos deliberadamente seleccionados y bounded. Model output conserva `model_invocation_id`, prompt/model version y etiqueta `model_derived=true`; nunca sobrescribe deterministic observations.
