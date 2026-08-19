"""Inference failures, typed by what the caller should do about them.

The distinction that matters: `ModelUnavailableError` means the request never got a
usable answer from the infrastructure and retrying later may work; `ModelOutputError`
means an answer arrived and was unusable, which retrying identically will not fix.
Blindly retrying the second is how a model gets to keep proposing nonsense.
"""


class InferenceError(Exception):
    """Base for every failure of the inference layer."""


class NoEndpointConfiguredError(InferenceError):
    """No endpoint serves the capability a task needs."""

    def __init__(self, capability: str) -> None:
        super().__init__(f"no model endpoint configured for capability: {capability}")
        self.capability = capability


class ModelUnavailableError(InferenceError):
    """The endpoint could not be reached, timed out, was saturated, or is tripped."""


class ModelOutputError(InferenceError):
    """The model answered with something that does not satisfy the contract.

    Carries no model text: a malformed completion may contain page content, and page
    content is untrusted data that should not travel into logs unbounded (docs/13).
    """
