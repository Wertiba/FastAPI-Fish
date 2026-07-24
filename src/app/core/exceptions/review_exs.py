from app.core.exceptions.base import EntityError


class ReviewNotFoundError(EntityError):
    pass


class ReviewAlreadyExistsError(EntityError):
    pass
