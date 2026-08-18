"""HTTP error contract.

One stable envelope with a machine-readable code, a safe message and the request id.
Codes are the same vocabulary as `contracts/cli-envelope.schema.json`, so the CLI can
map an API error to its envelope without inventing a second taxonomy.

Nothing here leaks tracebacks, SQL or internal state: unexpected failures become a
generic INTERNAL_ERROR that the caller can correlate by request id.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agentic_qa.application.errors import (
    AlreadyExistsError,
    IdempotencyConflictError,
    NotFoundError,
)
from agentic_qa.application.services.policy_resolution import PolicyNotResolvedError
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.runs.run import RunTransitionError
from agentic_qa.interfaces.http.request_context import REQUEST_ID_HEADER, get_request_id

logger = logging.getLogger(__name__)


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {"code": code, "message": message},
        "request_id": get_request_id(),
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={REQUEST_ID_HEADER: get_request_id()},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", str(error))

    @app.exception_handler(IdempotencyConflictError)
    async def _idempotency_conflict(_: Request, error: IdempotencyConflictError) -> JSONResponse:
        # 409 and never retried automatically: a reused key is a client bug, and
        # retrying it would run work the caller did not ask for (docs/12).
        return error_response(status.HTTP_409_CONFLICT, "CONFLICT", str(error))

    @app.exception_handler(AlreadyExistsError)
    async def _already_exists(_: Request, error: AlreadyExistsError) -> JSONResponse:
        return error_response(status.HTTP_409_CONFLICT, "CONFLICT", str(error))

    @app.exception_handler(PolicyNotResolvedError)
    async def _policy_not_resolved(_: Request, error: PolicyNotResolvedError) -> JSONResponse:
        # A run without a resolved policy has no origin allowlist, so refusing is the
        # only safe answer (docs/13).
        return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, "POLICY_DENIED", str(error))

    @app.exception_handler(RunTransitionError)
    async def _invalid_transition(_: Request, error: RunTransitionError) -> JSONResponse:
        return error_response(status.HTTP_409_CONFLICT, "CONFLICT", str(error))

    @app.exception_handler(InvalidEntityError)
    async def _invalid_entity(_: Request, error: InvalidEntityError) -> JSONResponse:
        return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR", str(error))

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            "request payload failed validation",
            details={"errors": jsonable_encoder(error.errors())},
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, error: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", type(error).__name__)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "internal error; correlate with the request id",
        )
