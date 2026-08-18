"""Application-level errors raised across port boundaries."""


class ApplicationError(Exception):
    """Base for failures the Application layer defines for its ports/use cases."""


class AlreadyExistsError(ApplicationError):
    """A repository rejected an insert because the identity is already taken.

    Adapters must raise this instead of leaking driver/ORM integrity errors, so a
    duplicate is never retried blindly as if it were a transient failure.
    """

    def __init__(self, entity: str, identity: str) -> None:
        super().__init__(f"{entity} already exists: {identity}")
        self.entity = entity
        self.identity = identity


class NotFoundError(ApplicationError):
    """A use case required an entity that does not exist."""

    def __init__(self, entity: str, identity: str) -> None:
        super().__init__(f"{entity} not found: {identity}")
        self.entity = entity
        self.identity = identity
