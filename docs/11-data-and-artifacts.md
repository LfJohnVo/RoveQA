# Data and Artifacts

## PostgreSQL tables — initial proposal

Introducir las tablas por fase, no en una mega migración. ✅ = ya migrada:

- `projects` ✅ (Phase 01), `environments`, `credential_refs`
- `user_stories` ✅ (Phase 01), `acceptance_criteria` ✅ (Phase 01), `test_cases`
- `test_plans`, `test_plan_versions`
- `runs` ✅ (Phase 01), `episodes`, `goals`
- `agent_actions`, `observations`, `verifications`, `findings`
- `recovery_points` ✅ (Phase 05; se llamaba `checkpoints` en el plan original — renombrada porque el checkpointer de LangGraph posee una tabla `checkpoints` propia y ambas colisionaban), `run_events` ✅ (Phase 03)
- `evidence_sets`, `artifacts`
- `idempotency_records`
- `model_invocations`
- `knowledge_candidates`, `memory_feedback`, `graph_sync_state` (Phase 09)

### Important identities

`run_id` identifica una ejecución durable.

`evidence_set_id` identifica una colección coherente de evidencia capturada dentro del mismo run/contexto. Artifacts que se materialicen juntos deben declarar el mismo `run_id` y el evidence set esperado.

`plan_id + plan_version` identifica exactamente la definición ejecutada. Nunca reportar una corrida histórica contra "la versión actual" del plan sin conservar la versión original.

## Artifact tree

```text
data/runs/{run_id}/
├── manifest.json
├── events.jsonl
├── evidence/
│   └── {evidence_set_id}/
│       ├── manifest.json
│       ├── observation.json
│       ├── screenshots/
│       ├── traces/
│       ├── network/
│       └── console/
├── browser/
│   ├── storage-state.json.enc-or-protected
│   └── fingerprints/
└── reports/
```

Artifacts grandes se escriben/streamean a filesystem; PostgreSQL guarda identidad, hash, tamaño, media type y path lógico.

## FailureBundle

El bundle consumible por agente/humano es una proyección de evidencia durable, no una carpeta construida con lecturas `latest` independientes.

```text
.roveqa/runs/{run_id}/failure/
├── manifest.json        # promoted LAST; presence == complete bundle
├── result.json
├── observation.json     # deterministic
├── hypothesis.json      # optional; model-derived
├── steps.json
├── console.jsonl
├── network.jsonl
├── screenshots/
├── trace/
└── video/
```

Materialization protocol:
1. Resolver `run_id`, `evidence_set_id`, plan/version y target fingerprint.
2. Verificar que cada artifact solicitado comparte esa provenance.
3. Escribir/stream a un directorio temporal sibling.
4. Verificar hash/tamaño cuando existan.
5. Promover artifacts.
6. Escribir/renombrar `manifest.json` al final.
7. Si falla cualquier paso, dejar `.partial` y nunca presentar el directorio como bundle completo.

## File-input safety
Todo file path recibido por CLI/API debe pasar guards apropiados: existencia/tipo, tamaño máximo, path policy cuando corresponda, schema/content validation y redacción de secretos. No leer un path arbitrario sólo porque un flag lo recibió.

## Bounded reads
History, steps y artifact metadata deben paginarse/streamearse o tener límites explícitos. Evitar acumuladores sin cota y `response.json()` de respuestas potencialmente enormes sin un límite de bytes.

## Data retention
Policy configurable por project/environment. Screenshots/traces pueden contener PII; no asumir retención infinita. Crear abstraction `ArtifactRepository` para migrar a S3/MinIO sin tocar Domain.


## Knowledge projection
FalkorDB no reemplaza estas tablas. Guarda una proyección temporal/relation-friendly derivada de `knowledge_candidates` promovidos. Cada graph entity/edge reusable conserva candidate/provenance identity suficiente para auditar o rebuild.

El filesystem/PostgreSQL siguen guardando raw evidence; nunca insertar screenshots, HAR completos, cookies o secretos como graph payloads.
