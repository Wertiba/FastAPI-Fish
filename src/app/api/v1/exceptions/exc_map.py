from app.api.v1.exceptions.api_exs import (
    Conflict,
    Forbidden,
    Inactive,
    NotFound,
    Unauthorized,
    ValidationFailed,
)
from app.core.exceptions.base import UnprocessableEntityError
from app.core.exceptions.user_exs import (
    ForbiddenError,
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotActiveError,
    UserNotFoundError,
)

DOMAIN_TO_API: dict[type, callable] = {
    UserNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="User not found",
    ),
    ForbiddenError: lambda path, exc=None: Forbidden(
        path=path,
    ),
    InvalidCredentialsError: lambda path, exc=None: Unauthorized(
        path=path,
    ),
    InvalidPasswordError: lambda path, exc=None: Unauthorized(
        path=path,
    ),
    UserAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="User already exists",
    ),
    UnprocessableEntityError: lambda path, exc=None: ValidationFailed(
        path=path,
    ),
    UserNotActiveError: lambda path, exc=None: Inactive(
        path=path,
    ),
}
