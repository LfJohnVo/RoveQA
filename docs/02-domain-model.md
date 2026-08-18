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
