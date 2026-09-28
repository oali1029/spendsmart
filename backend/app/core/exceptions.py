"""Domain exceptions raised by the service layer.

They deliberately carry no HTTP details: the service layer doesn't know it is behind a web API.
app/main.py maps them to status codes.
"""


class NotFoundError(Exception):
    """A requested resource does not exist (mapped to HTTP 404)."""


class ConflictError(Exception):
    """The request conflicts with current state, e.g. a duplicate name (mapped to HTTP 409)."""
