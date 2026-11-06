from app.shared.domain.errors import EntityError


class UserNotFoundError(EntityError):
    pass


class UserAlreadyExistsError(EntityError):
    def __init__(self, email: str) -> None:
        super().__init__(email)
        self.email = email
