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


class IdempotencyConflictError(ApplicationError):
    """An idempotency key was reused for a different logical request.

    Failing typed is the point: silently running the new request would break the
    promise the key makes, and replaying the old response would answer a question the
    client did not ask.
    """

    def __init__(self, scope: str, key: str) -> None:
        super().__init__(f"idempotency key reused with a different request: {scope}/{key}")
        self.scope = scope
        self.key = key


class AuthenticationRequiredError(ApplicationError):
    """No credential, or one nobody issued.

    An application concern rather than an HTTP one, which is why it lives beside the
    others: the delivery layer maps it to `401` the same way it maps `NotFoundError` to
    `404`, and a second adapter would map it to whatever it says (ADR 0020).
    """


class ForbiddenError(ApplicationError):
    """A real credential that does not reach the resource.

    Kept apart from the above deliberately: "you did not authenticate" and "you
    authenticated as someone who may not do that" send a person to different places, and
    a client that cannot tell them apart retries the wrong one.
    """
