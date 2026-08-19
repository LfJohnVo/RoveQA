"""Latency, token and error accounting per endpoint.

Deliberately in-process counters plus a structured log line per call: the numbers a
single-node deployment needs to answer "is the model the bottleneck, and how much is it
being asked to read?" without adding a metrics backend before there is one to scrape.

Prompts and completions are never recorded here. They contain page content, which is
untrusted data, and may contain fixture credentials (docs/13).
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EndpointStats:
    calls: int = 0
    failures: int = 0
    invalid_outputs: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_latency_ms: float = 0.0

    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.calls if self.calls else 0.0


@dataclass
class InferenceMetrics:
    by_endpoint: dict[str, EndpointStats] = field(default_factory=dict)

    def _stats(self, endpoint: str) -> EndpointStats:
        return self.by_endpoint.setdefault(endpoint, EndpointStats())

    def record_call(
        self,
        *,
        endpoint: str,
        task: str,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        stats = self._stats(endpoint)
        stats.calls += 1
        stats.total_latency_ms += latency_ms
        stats.prompt_tokens += prompt_tokens
        stats.completion_tokens += completion_tokens
        logger.info(
            "inference ok endpoint=%s task=%s latency_ms=%.0f prompt_tokens=%d "
            "completion_tokens=%d",
            endpoint,
            task,
            latency_ms,
            prompt_tokens,
            completion_tokens,
        )

    def record_failure(self, *, endpoint: str, task: str, reason: str) -> None:
        stats = self._stats(endpoint)
        stats.calls += 1
        stats.failures += 1
        logger.warning("inference failed endpoint=%s task=%s reason=%s", endpoint, task, reason)

    def record_invalid_output(self, *, endpoint: str, task: str, reason: str) -> None:
        """Counted apart from failures: the endpoint answered, the answer was unusable.

        A rising count here points at the prompt or the model choice, not at the box.
        """
        stats = self._stats(endpoint)
        stats.invalid_outputs += 1
        logger.warning("inference rejected endpoint=%s task=%s reason=%s", endpoint, task, reason)
