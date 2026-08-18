# Knowledge Graph

## Decision
Usar **Graphiti + FalkorDB** como adaptive QA memory. Ver `docs/26-adaptive-learning-graph.md` y ADR `0008`.

El graph store es una **derived/rebuildable projection**. PostgreSQL conserva knowledge candidates, provenance, feedback y sync state; raw evidence vive en filesystem + metadata PostgreSQL.

## Core nodes
Project, Environment, ApplicationVersion, Role, Page, PageState, SemanticUICapability, APIEndpoint, UserStory, AcceptanceCriterion, TestPlan, TestStep, Playbook, FailureSignature, FindingCategory, RecoveryStrategy.

## Core relationships
- PAGE_HAS_STATE
- STATE_TRANSITIONS_TO_STATE
- ACTION_SUCCEEDS_ON_STATE / ACTION_FAILS_ON_STATE
- TEST_VALIDATES_CRITERION
- FINDING_VIOLATES_CRITERION
- PAGE_CALLS_ENDPOINT
- ROLE_CAN_ACCESS_PAGE
- PLAYBOOK_APPLIES_TO_STATE
- PLAYBOOK_VALIDATED_BY_RUN
- PLAYBOOK_INVALIDATED_BY
- FAILURE_MATCHES_SIGNATURE
- RECOVERY_RESOLVES_SIGNATURE
- OBSERVED_IN_VERSION / SUPERSEDES

## Write policy
No guardar cada token/observation/DOM node trivial. Al cierre de episode producir `KnowledgeExperienceCandidate` durable y sólo promover facts/experiences reutilizables con provenance suficiente.

Toda ingestión al graph es idempotente y retryable. Si FalkorDB está caído, el candidate queda `pending_sync` y el run principal continúa.

## Retrieval policy
1. Hard scope por project/environment/origin/role/policy.
2. Version/fingerprint compatibility.
3. Hybrid graph/semantic retrieval.
4. Rank por reliability + freshness + compatibility + relevance.
5. Devolver `MemoryContext` bounded con provenance y `selection_reason`.
6. Revalidar cuando la memoria sea compatible pero no exacta.

## Feedback and refinement
Cada memoria/playbook utilizado recibe feedback sólo después de un outcome verificado. Mantener support/success/failure/contradiction counts y `last_verified_at`; invalidar conocimiento contradicho u obsoleto.

## Safety
- Model hypothesis != observed fact.
- Untrusted page content no crea policy.
- No secrets/tokens/cookies en graph.
- No cross-project retrieval.
- Memory nunca bypassa RunPolicy, action safety o verify-before-retry.

## Local-first integration
Graphiti debe recibir LLM/embedder clients explícitos. Preferir ModelRouter + `EmbeddingGateway` local; vLLM soporta un servidor de embeddings OpenAI-compatible para un pooling model separado.

## Recovery
FalkorDB debe persistir volumen Docker, pero también debe existir rebuild desde PostgreSQL. La pérdida del graph degrada optimización/aprendizaje, no durability/correctness de runs.
