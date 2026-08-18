"""Verify before retry.

The mandatory case from docs/05: the target processed `Create User`, then the worker
died before the acknowledgement. Repeating the action blindly creates a duplicate;
skipping it loses the work. So the only safe move is to *ask the target* whether the
effect landed, using a marker the run itself chose.

That marker is why side-effecting actions must carry an idempotency strategy: without
a run-scoped reference there is nothing to ask about.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SideEffectOutcome:
    performed: bool
    """False when verification found the effect had already landed."""

    verified: bool
    """Whether the effect is confirmed present after this call."""


async def perform_once(
    *,
    verify: Callable[[], Awaitable[bool]],
    perform: Callable[[], Awaitable[None]],
    description: str = "side effect",
) -> SideEffectOutcome:
    """Perform an effect at most once, deciding by observation rather than by memory."""
    if await verify():
        logger.info("%s already present; not repeating it", description)
        return SideEffectOutcome(performed=False, verified=True)

    await perform()
    confirmed = await verify()
    if not confirmed:
        # Reported honestly rather than assumed: an unconfirmed write is not a
        # success, and the caller decides whether to escalate.
        logger.warning("%s could not be confirmed after performing it", description)
    return SideEffectOutcome(performed=True, verified=confirmed)
