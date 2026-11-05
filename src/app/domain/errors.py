class EntityError(Exception):
    """Base for business-rule failures; the presentation layer maps each subclass to an HTTP error."""


class UnprocessableEntityError(EntityError):
    pass
