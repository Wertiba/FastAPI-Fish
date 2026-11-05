"""Domain error -> API error. The first ``isinstance`` match wins, so list subclasses before their bases."""

from collections.abc import Callable
from typing import Any

from app.domain.errors import UnprocessableEntityError
from app.domain.users.errors import (
    ForbiddenError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotActiveError,
    UserNotFoundError,
)
from app.presentation.http.api.v1.exceptions.api_exs import (
    EmailAlreadyExists,
    Forbidden,
    Inactive,
    NotFound,
    Unauthorized,
    ValidationFailed,
)
from app.presentation.http.api.v1.exceptions.base import APIException

DOMAIN_TO_API: dict[type[Exception], Callable[[str, Any], APIException]] = {
    UserNotFoundError: lambda path, exc: NotFound(
        path=path,
        message="User not found",
    ),
    ForbiddenError: lambda path, exc: Forbidden(
        path=path,
    ),
    InvalidCredentialsError: lambda path, exc: Unauthorized(
        path=path,
    ),
    UserAlreadyExistsError: lambda path, exc: EmailAlreadyExists(
        path=path,
        details={"field": "email", "value": exc.email},
    ),
    UserNotActiveError: lambda path, exc: Inactive(
        path=path,
    ),
    UnprocessableEntityError: lambda path, exc: ValidationFailed(
        path=path,
    ),
}
