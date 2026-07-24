from app.core.exceptions.base import EntityError


class UserNotFoundError(EntityError):
    pass


class ForbiddenError(EntityError):
    pass


class InvalidPasswordError(EntityError):
    pass


class UserAlreadyExistsError(EntityError):
    pass


class InvalidCredentialsError(EntityError):
    pass


class UserNotActiveError(EntityError):
    pass


class DeficiencyApproversError(EntityError):
    pass
