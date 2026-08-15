"""Controlled application errors shared by the V2.3A services."""


class V2ApplicationError(Exception):
    """Base class whose messages are safe for the API client."""


class V2NotFoundError(V2ApplicationError):
    pass


class V2ConflictError(V2ApplicationError):
    pass


class V2InvalidRequestError(V2ApplicationError):
    pass
