"""Realtime run events over WebSocket.

Connect order matters and is the whole point of this handler:

1. open the subscription (anchors the stream position),
2. send durable catch-up from `run_events`,
3. relay live events, skipping anything already covered by the catch-up.

Doing it in that order means an event published while history is being read is
delivered instead of lost, and a client always ends up with a complete, in-order
view even though realtime delivery itself is best-effort.
"""

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from agentic_qa.application.queries.list_run_events import list_run_events
from agentic_qa.interfaces.http.dependencies import container_from_websocket
from agentic_qa.interfaces.http.schemas import RunEventResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

CLOSE_RUN_NOT_FOUND = 4404
CLOSE_REALTIME_UNAVAILABLE = 4503


@router.websocket("/ws/runs/{run_id}")
async def run_events_socket(
    websocket: WebSocket, run_id: str, after: int = Query(default=0, ge=0)
) -> None:
    container = container_from_websocket(websocket)
    await websocket.accept()

    subscription = None
    if container.events is not None:
        try:
            subscription = await container.events.subscribe(run_id)
        except Exception:  # noqa: BLE001 - realtime is optional, catch-up is not
            logger.warning("realtime subscribe failed for run %s", run_id, exc_info=True)

    try:
        async with container.unit_of_work() as uow:
            history = await list_run_events(uow, run_id, after=after, limit=500)
    except Exception:
        await websocket.close(code=CLOSE_RUN_NOT_FOUND)
        if subscription is not None:
            await subscription.aclose()
        return

    last_sequence = after
    for event in history:
        await websocket.send_json(RunEventResponse.from_domain(event).model_dump(mode="json"))
        last_sequence = event.sequence

    if subscription is None:
        # The client has a complete baseline; tell it to fall back to REST polling
        # rather than pretending it is receiving live updates.
        await websocket.close(code=CLOSE_REALTIME_UNAVAILABLE)
        return

    try:
        async for event in subscription:
            if event.sequence <= last_sequence:
                continue  # already delivered by the catch-up
            last_sequence = event.sequence
            await websocket.send_json(RunEventResponse.from_domain(event).model_dump(mode="json"))
    except WebSocketDisconnect:
        logger.debug("client disconnected from run %s", run_id)
    finally:
        await subscription.aclose()
        if websocket.client_state is WebSocketState.CONNECTED:
            await websocket.close()
