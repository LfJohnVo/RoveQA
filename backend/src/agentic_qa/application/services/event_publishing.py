"""Best-effort realtime publishing."""

import logging

from agentic_qa.application.ports.events import RunEvent
from agentic_qa.application.ports.streams import RunEventPublisher

logger = logging.getLogger(__name__)


async def publish_best_effort(publisher: RunEventPublisher | None, event: RunEvent) -> None:
    """Fan out an already-committed event, swallowing transport failures.

    The broad catch is deliberate and safe *because* the event is durable before this
    runs: a Redis outage must degrade realtime latency, never the run. Clients repair
    from the durable log, so a dropped publish costs nothing but freshness.
    """
    if publisher is None:
        return
    try:
        await publisher.publish(event)
    except Exception:  # noqa: BLE001 - realtime is optional, the run is not
        logger.warning(
            "realtime publish failed for run %s seq %s; durable log unaffected",
            event.run_id,
            event.sequence,
            exc_info=True,
        )
