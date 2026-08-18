# Runtime Knowledge / Adaptive Memory Rules

Aplica a `backend/**/knowledge/**`, `backend/**/memory/**`, graph adapters, graph contracts y Phase 09.

- PostgreSQL owns durable knowledge candidates, provenance, feedback and graph sync state.
- FalkorDB/Graphiti is a derived, rebuildable projection for retrieval/traversal; never authoritative run state.
- Domain/Application reference ports only; Graphiti/FalkorDB imports stay in Infrastructure.
- No raw secrets, passwords, tokens, cookies or unrestricted page content in the graph.
- Model-derived hypotheses remain labelled and cannot silently become observed facts.
- Retrieval must enforce project/environment/role/policy/version/fingerprint scope before semantic ranking.
- Every returned memory item carries reliability, temporal validity and provenance.
- Fingerprint mismatch or contradiction forces revalidation; trusted playbooks still obey RunPolicy and verify-before-retry.
- Consolidation and graph writes are idempotent. Graph downtime leaves durable candidates pending and must not fail the primary run.
- A graph rebuild from PostgreSQL candidates/history must be supported and tested.
