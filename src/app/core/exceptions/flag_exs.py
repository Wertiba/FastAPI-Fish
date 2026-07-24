from app.core.exceptions.base import EntityError


class FlagNotFoundError(EntityError):
    pass


class FlagAlreadyExistsError(EntityError):
    pass
