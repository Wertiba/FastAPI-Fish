from app.core.exceptions.base import EntityError


class EventNotFoundError(EntityError):
    pass


class EventAlreadyExistsError(EntityError):
    pass
