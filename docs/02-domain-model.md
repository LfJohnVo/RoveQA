# Domain Model

## Bounded contexts

### Projects
`Project`, `TargetApplication`, `Environment`, `CredentialReference`, `RunPolicy`.

### QA
`UserStory`, `AcceptanceCriterion`, `TestCase`, `Finding`, `EvidenceReference`, `Severity`.

### Runs
`Run`, `Episode`, `Goal`, `RunStatus`, `CheckpointReference`, `RecoveryPoint`.

### Agent
`Plan`, `Observation`, `AgentAction`, `Verification`, `Decision`, `ActionOutcome`.

### Browser
`BrowserSession`, `PageState`, `PageFingerprint`, `BrowserAction`, `LocatorHint`, `BrowserArtifact`.

### Inference
`InferenceRequest`, `InferenceResult`, `TaskType`, `ModelCapability`, `ModelPolicy`.

### Knowledge
`KnowledgeExperienceCandidate`, `KnowledgeFact`, `Experience`, `Playbook`, `FailureSignature`, `MemoryContext`, `MemoryFeedback`, `GraphSyncState`, `ApplicationStateNode`, `Relationship`.

## Core statuses

RunStatus:
`CREATED | QUEUED | RUNNING | PAUSING | PAUSED | RECOVERING | CANCELLING | CANCELLED | FAILED | COMPLETED`.

ActionStatus:
`PLANNED | PREPARED | EXECUTING | EXECUTED | VERIFYING | VERIFIED | FAILED | RECOVERING | SKIPPED`.

Verdict (domain value, outcome QA de un run terminal):
`PASSED | FAILED | BLOCKED | INCONCLUSIVE | CANCELLED`.

Mapping RunStatus ↔ Verdict:
- `RunStatus` es el estado de lifecycle; `Verdict` es el resultado QA y sólo existe en runs terminales.
- `COMPLETED` significa que el workflow terminó de evaluar el plan y porta cualquier verdict (`passed`, `failed`, `blocked`, `inconclusive`).
- `FAILED` significa fallo de infraestructura/runtime (no del producto) y mapea a verdict `inconclusive` salvo evidencia suficiente para `blocked`.
- `CANCELLED` mapea a verdict `cancelled`.
- Un verdict nunca se infiere del exit code del proceso ni del status HTTP; es un valor persistido del dominio (ver `plans/phase-08-agent-first-cli.md` y `contracts/failure-bundle.schema.json`).

## Action safety fields
Cada `AgentAction` con side effect debe registrar:
- action_id estable
- intent
- preconditions
- execution payload tipado
- expected postconditions
- side_effect boolean
- idempotency strategy
- verification strategy
- actual outcome
- artifact refs

## Important invariants
- Un `Run` sólo se considera avanzado hasta un recovery point durable confirmado.
- Un `Finding` debe apuntar a evidencia suficiente para reproducir/inspeccionar.
- Un `Playbook` aprendido debe asociarse al fingerprint/version context que lo hace válido.
- Un memory item operativo debe tener provenance durable y reliability/temporal validity.
- Graph nodes/edges son projection data; promotion/invalidation decisions deben poder reconstruirse desde PostgreSQL.
