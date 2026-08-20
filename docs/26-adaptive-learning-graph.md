# Adaptive QA Learning Graph

## Goal
Hacer que RoveQA sea progresivamente más eficiente sin entrenar pesos del modelo: aprender **qué estados existen, qué transiciones funcionan, qué recorridos son confiables, qué fallos se repiten y bajo qué contexto**.

El grafo es memoria operacional con evidence, no una autoridad que pueda contradecir el estado durable o la policy.

## Storage model

```text
RAW / AUTHORITATIVE                         LEARNED PROJECTION

PostgreSQL + filesystem                    Graphiti + FalkorDB
-----------------------                    ------------------
runs                                       Pages / States
episodes                                   Transitions
actions                                    Playbooks
verifications             consolidate      Failure signatures
findings                 ------------->    Acceptance relations
evidence sets                               Role/API relations
knowledge_candidates                        Temporal validity
memory_feedback

        ^                                           |
        |--------------- rebuild -------------------|
```

FalkorDB puede borrarse y reconstruirse. PostgreSQL no.

## Why a graph
La información útil del navegador es relacional:

```text
Role(Admin)
  -> CAN_ACCESS -> Page(Users)
  -> HAS_STATE -> State(UserList)
  -> TRANSITION(click create) -> State(CreateUserForm)
  -> TRANSITION(submit valid form) -> State(UserCreated)
  -> VALIDATES -> AcceptanceCriterion(AC-12)
```

Una búsqueda vectorial plana puede encontrar texto parecido; el grafo permite además responder paths, dependencias, versiones y contexto de validez.

## Runtime components

### KnowledgeRepository port
Operaciones de application-level knowledge sin tipos Graphiti/FalkorDB.

### KnowledgeCandidateRepository
Adapter durable PostgreSQL para candidates, provenance, promotion status, feedback y sync state.

### GraphMemoryAdapter
Infrastructure adapter de `KnowledgeRepository` implementado con Graphiti + FalkorDB.

### MemoryRetriever
Construye un `MemoryContext` bounded para el planner.

### ExperienceConsolidator
Convierte episodios cerrados/verificados en `KnowledgeExperienceCandidate` idempotentes.

### MemoryFeedbackRecorder
Después de usar memoria, registra si el outcome verificado fue success/failure/contradiction/stale/unsafe.

### GraphRebuilder
Reproduce candidates/promotions desde PostgreSQL hacia un FalkorDB vacío.

## Learning lifecycle

```text
Browser/QA execution
      |
      v
verified Episode / ActionOutcome
      |
      v
KnowledgeExperienceCandidate (PostgreSQL)
      |
      +---- redaction / provenance / quality gates
      |
      v
KnowledgeConsolidationActivity
      |
      v
Graphiti -> FalkorDB
      |
      v
next run: Retrieve Memory
      |
      v
Planner uses candidate
      |
      v
Verify real outcome
      |
      v
MemoryFeedback -> reliability / invalidation
```

Graph downtime stops at `pending_sync`; it does not fail the run.

## What to learn

### Nodes
- Project
- Environment
- ApplicationVersion
- Role
- Page
- PageState
- Form / semantic UI capability
- APIEndpoint
- TestPlan / TestStep
- UserStory / AcceptanceCriterion
- Playbook
- FailureSignature
- FindingCategory
- RecoveryStrategy

No crear un node por cada token o cada DOM element efímero.

### Relationships
- `PAGE_HAS_STATE`
- `STATE_TRANSITIONS_TO_STATE`
- `ACTION_SUCCEEDS_ON_STATE`
- `ACTION_FAILS_ON_STATE`
- `PLAYBOOK_APPLIES_TO_STATE`
- `PLAYBOOK_VALIDATED_BY_RUN`
- `PLAYBOOK_INVALIDATED_BY`
- `TEST_VALIDATES_CRITERION`
- `FINDING_VIOLATES_CRITERION`
- `PAGE_CALLS_ENDPOINT`
- `ROLE_CAN_ACCESS_PAGE`
- `FAILURE_MATCHES_SIGNATURE`
- `RECOVERY_RESOLVES_SIGNATURE`
- `OBSERVED_IN_VERSION`
- `SUPERSEDES`

## Provenance required
Cada reusable fact/playbook debe poder volver a evidencia durable:

```text
candidate_id
source_run_id
source_episode_id
evidence_set_id
test_plan_version
app_version/page_fingerprint
observed/model_derived
created_at/last_verified_at
```

Un memory item sin provenance no entra al planner.

## Promotion policy
Default inicial, configurable y evaluable:

- **candidate**: un outcome verificado suficiente para proponer memoria;
- **promoted**: al menos 2 supports compatibles y sin contradicción crítica, o un deterministic fact directamente verificable;
- **trusted playbook**: varios éxitos independientes, reliability alta y fingerprint/version compatible;
- **invalidated**: contradicción verificada, fingerprint incompatible o cambio explícito de producto.

Los thresholds exactos se configuran y se ajustan por benchmark, no por intuición. Incluso `trusted` exige RunPolicy + precondition verification.

Estados adicionales del contrato (`contracts/knowledge-experience.schema.json`): `rejected` (candidato descartado en consolidación, nunca promovido) y `pending_sync` (durable en PostgreSQL, aún no materializado en el graph por outage/backlog; no es un tier de promoción).

## Reliability
Mantener contadores deterministas (`success_count`, `failure_count`, `contradiction_count`, `last_verified_at`). No usar una única confidence producida por LLM como reliability operacional.

Fórmula implementada (Phase 09, `domain/knowledge/experience.py`):

```text
against     = failure_count + 2 * contradiction_count
reliability = success_count / (success_count + against)      # 0.0 sin evidencia
```

Dos decisiones explícitas frente a una Beta suavizada:

- **Sin evidencia es 0.0, no 0.5.** Una afirmación no probada no debe arrancar pareciendo perfecta: el ranking la pondría por encima de todo lo que sí se verificó.
- **Una contradicción pesa doble que un failure.** Un failure dice "esta vez no funcionó"; una contradicción dice "esto es falso". Pesarlos igual dejaría sobrevivir conocimiento contradicho.

`reliability` se recalcula siempre desde los contadores y se persiste sólo para poder ordenar en SQL; nunca se escribe de forma independiente de ellos.

## Retrieval pipeline

### 1. Hard filters
Antes de semantic/hybrid search:
- project/tenant exacto;
- environment permitido;
- origin/policy compatible;
- role compatible;
- app version/fingerprint compatible o marcado `revalidate`;
- no invalidated/rejected;
- no secret-bearing content.

### 2. Candidate search
Hybrid search/traversal por goal, page/state, test step, failure signature y relaciones.

Implementado en Phase 09: el pool de candidates se lee de PostgreSQL (scope + status accionable, ordenado por reliability) y el grafo **amplía** ese pool, nunca lo autoriza. Un FalkorDB caído, vacío o manipulado puede como máximo sugerir candidates existentes distintos; no puede inventar conocimiento ni cambiar lo que uno dice.

### 3. Ranking
Combinar deterministic signals:
- fingerprint/version compatibility;
- reliability;
- freshness/last verified;
- graph distance/relation usefulness;
- semantic relevance.

### 4. Bounded context
Devolver pocos items de alto valor (`MemoryContext`), no volcar el subgrafo entero al prompt. Default 8 items, techo de contrato 50.

El ranking es determinista y vive en el Domain: `compatibility × source × reliability × (0.5 + 0.5 × freshness)`, con desempate por `candidate_id` para que las mismas entradas produzcan siempre el mismo orden — un benchmark cold-vs-warm no puede estar midiendo orden de diccionario. `freshness` decae a la mitad cada 30 días y sólo escala la mitad del peso, así que la edad baja la prioridad de un hecho pero nunca lo elimina por sí sola.

### 5. Revalidation
`compatibility=revalidate` obliga a comprobar preconditions antes de seguir el playbook.

## Negative learning
Guardar también experiencias negativas reutilizables:
- transición que repetidamente no funciona en cierto state/version;
- ruta que lleva a login/error;
- failure signature conocida;
- locator hint obsoleto;
- playbook contradicho.

Esto evita que el agente repita intentos inútiles.

## Local inference
Graphiti permite inyectar LLM/embedder. RoveQA no usa sus defaults hosted en producción local-first.

```text
Graphiti adapter
  |-- LLM client -> ModelRouter / local OpenAI-compatible generation endpoint
  |-- Embedder   -> EmbeddingGateway -> vLLM pooling /v1/embeddings
  `-- Driver     -> FalkorDB
```

El embedding model es una instancia separada del modelo de GUI si hace falta; debe poder arrancarse bajo un Docker profile de memory/GPU.

## Security / poisoning controls
- Page text es untrusted source, nunca policy.
- Secrets/credentials se redaccionan antes de candidate creation.
- Hypotheses conservan `model_derived=true`.
- No cross-project retrieval.
- No promotion automática de instrucciones encontradas en la web.
- Findings/observations con PII siguen retention policy.
- Un playbook no puede introducir origins/actions fuera de RunPolicy.

## Rebuild and repair
Mantener `graph_sync_state` y un command/API administrativo:

```text
roveqa memory status
roveqa memory rebuild --project <id>
roveqa memory validate --project <id>
```

Rebuild consume durable candidates/promotions; no necesita reejecutar los tests.

## Metrics
- memory retrieval hit rate
- memory accepted/useful rate
- revalidation rate
- stale/contradiction rate
- playbook success rate
- knowledge sync lag
- graph write/retrieval latency
- planner model calls saved vs cold baseline
- browser actions saved vs cold baseline
- warm-run verdict quality vs cold baseline

## Success criterion
El grafo sólo se considera útil si un benchmark repetible demuestra reducción de model calls/acciones/latencia de decisión **sin degradar correctness ni evidencia**.
