class EntityError(Exception):
    """Base for business-rule failures; the presentation layer maps each subclass to an HTTP error."""


class UnprocessableEntityError(EntityError):
    pass


class ForbiddenError(EntityError):
    """The caller is authenticated but may not perform the operation."""


class InvalidCredentialsError(EntityError):
    """Missing or invalid token, wrong email or password."""
