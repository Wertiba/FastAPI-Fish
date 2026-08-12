from app.core.exceptions.base import EntityError


class UserNotFoundError(EntityError):
    pass


class ForbiddenError(EntityError):
    pass


class InvalidPasswordError(EntityError):
    pass


class UserAlreadyExistsError(EntityError):
    def __init__(self, email: str):
        super().__init__(email)
        self.email = email


class InvalidCredentialsError(EntityError):
    pass


class UserNotActiveError(EntityError):
    pass
