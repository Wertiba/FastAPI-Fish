from fastapi import status

from app.modules.auth.domain.errors import UserNotActiveError
from app.shared.presentation.http.errors import APIException
from app.shared.presentation.http.errors.mapping import ErrorMap


class Inactive(APIException):
    status_code = status.HTTP_423_LOCKED
    code = "USER_INACTIVE"
    message = "The user has been deactivated"


AUTH_ERRORS: ErrorMap = {
    UserNotActiveError: lambda path, exc: Inactive(path=path),
}
