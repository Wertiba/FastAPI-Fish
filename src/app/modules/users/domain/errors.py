from app.shared.domain.errors import ConflictError, LockedError, NotFoundError


class UserNotFoundError(NotFoundError):
    default_message = "User not found"


class EmailAlreadyExistsError(ConflictError):
    code = "EMAIL_ALREADY_EXISTS"
    default_message = "User with this email already exists"

    def __init__(self, email: str) -> None:
        super().__init__(details={"field": "email", "value": email})


class UserInactiveError(LockedError):
    code = "USER_INACTIVE"
    default_message = "The user has been deactivated"
