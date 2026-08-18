# Agent-first CLI contracts, not TestSprite runtime dependency

Status: Accepted

## Context
TestSprite CLI demonstrates strong agent-facing testing contracts, but its repository is intentionally a thin client to a hosted platform. RoveQA requires self-hosted browser execution, local model inference, durable workflows and first-party memory.

## Decision
Keep the existing RoveQA runtime architecture. Add a thin TypeScript `roveqa` CLI in Phase 08 that talks only to FastAPI and adopts original implementations of these patterns: stable JSON/exit codes, versioned TestPlan files, idempotent mutation triggers, bounded wait/polling, runtime response validation, atomic self-consistent FailureBundles, dry-run/lint/scaffold, rerun/diff/flaky and agent verification installation.

## Consequences
- TestSprite is a design reference, not a product/runtime dependency.
- CLI and React UI are sibling Interface/Delivery adapters over the same application contracts.
- FastAPI/API schemas become a public compatibility surface and require versioning/contract tests.
- Plan and failure-bundle schemas are first-class version-controlled artifacts.
- Release gates include agent-driven CLI verification and bundle integrity.
