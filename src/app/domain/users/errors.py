from app.domain.errors import EntityError


class UserNotFoundError(EntityError):
    pass


class ForbiddenError(EntityError):
    pass


class UserAlreadyExistsError(EntityError):
    def __init__(self, email: str) -> None:
        super().__init__(email)
        self.email = email


class InvalidCredentialsError(EntityError):
    """Missing or invalid token, wrong email or password."""


class UserNotActiveError(EntityError):
    pass
