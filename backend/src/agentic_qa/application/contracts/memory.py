"""The portable MemoryContext document (`contracts/memory-context.schema.json`).

One direction only, unlike the knowledge document. A memory context is something this
system *produces* — for a planner prompt, an API response, a trace a human reads. It
is never accepted from outside, because accepting one would let a caller hand the
agent a set of "memories" that never passed a scope filter or a promotion gate.
"""

from typing import Any

from agentic_qa.domain.knowledge.memory_context import (
    SCHEMA_VERSION,
    MemoryContext,
    MemoryItem,
)


def to_document(context: MemoryContext) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "query_id": context.query_id,
        "project_id": context.project_id,
        "environment_id": context.environment_id,
        "items": [_item_document(item) for item in context.items],
    }


def _item_document(item: MemoryItem) -> dict[str, Any]:
    return {
        "memory_id": item.memory_id,
        "kind": item.kind,
        "summary": item.summary,
        # These two labels are required by the contract and never derived from each
        # other: a consumer must be able to tell a verified observation from a model's
        # hypothesis without inferring it from anything else in the document.
        "observed": item.observed,
        "model_derived": item.model_derived,
        "reliability": item.reliability,
        "freshness": item.freshness,
        "validity": {
            "valid_from": item.valid_from.isoformat(),
            "valid_to": item.valid_to.isoformat() if item.valid_to else None,
            "last_verified_at": (
                item.last_verified_at.isoformat() if item.last_verified_at else None
            ),
        },
        "compatibility": item.compatibility.value,
        "provenance": {
            "source_run_id": item.source_run_id,
            "candidate_id": item.candidate_id,
            "evidence_set_id": item.evidence_set_id,
        },
        "selection_reason": item.selection_reason,
    }
