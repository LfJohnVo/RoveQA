"""Circuit breaker for a model endpoint.

When a GPU box is down, thirty-second timeouts turn a run into a very slow way of
discovering the same thing repeatedly. After enough consecutive transport failures the
breaker opens and calls fail immediately, so the run reports "model unavailable" in
seconds instead of stalling; after a cooldown one call is allowed through to test the
water.

Only *transport* failures count. A model that answers with unusable output is answering
— tripping on that would take a working endpoint offline over a prompt problem.
"""

import time
from collections.abc import Callable


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        reset_after_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self._threshold = failure_threshold
        self._reset_after = reset_after_seconds
        self._clock = clock
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None

    def allow(self) -> bool:
        """True when a call may be attempted, half-opening after the cooldown."""
        if self._opened_at is None:
            return True
        if self._clock() - self._opened_at >= self._reset_after:
            # Half-open: let exactly one call through. It either closes the breaker on
            # success or re-opens it on failure.
            self._opened_at = None
            return True
        return False

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            self._opened_at = self._clock()
