"""Domain error hierarchy.

Domain errors never carry HTTP status codes; Interfaces map them at the boundary.
"""


class DomainError(Exception):
    """Base for every violated domain invariant."""


class InvalidEntityError(DomainError):
    """An entity was constructed with values its invariants forbid."""
