from fastapi import status

from app.modules.users.domain.errors import UserAlreadyExistsError, UserNotFoundError
from app.shared.presentation.http.errors import APIException, NotFound
from app.shared.presentation.http.errors.mapping import ErrorMap


class EmailAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    code = "EMAIL_ALREADY_EXISTS"
    message = "User with this email already exists"


USERS_ERRORS: ErrorMap = {
    UserNotFoundError: lambda path, exc: NotFound(path=path, message="User not found"),
    UserAlreadyExistsError: lambda path, exc: EmailAlreadyExists(
        path=path,
        details={"field": "email", "value": exc.email},
    ),
}
