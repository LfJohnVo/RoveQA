"""Contract versions the server speaks.

The CLI validates plans against schema files it ships. Those files and the server's
can drift — a CLI installed months ago will happily lint a plan the server then
rejects, and the error would surface as a validation failure with no hint that the
versions disagree. This endpoint lets a client compare before it gets there.

Unauthenticated and free of run data on purpose: it is the one thing a client needs
before it knows whether it can talk to this server at all.
"""

from fastapi import APIRouter

from agentic_qa.application.queries.failure_context import BUNDLE_SCHEMA_VERSION
from agentic_qa.application.queries.run_report import REPORT_VERSION
from agentic_qa.domain.qa.test_plan import SCHEMA_VERSION as TEST_PLAN_VERSION

router = APIRouter(prefix="/api/v1/meta", tags=["ops"])

API_VERSION = "v1"


@router.get("/contracts")
async def read_contracts() -> dict[str, object]:
    """The versions this server reads and writes."""
    return {
        "api_version": API_VERSION,
        "contracts": {
            "test_plan": TEST_PLAN_VERSION,
            "failure_bundle": BUNDLE_SCHEMA_VERSION,
            "run_report": REPORT_VERSION,
        },
    }
