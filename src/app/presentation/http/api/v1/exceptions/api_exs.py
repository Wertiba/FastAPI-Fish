from fastapi import status

from app.presentation.http.api.v1.exceptions.base import APIException


class BadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    message = "Invalid request"


class Unauthorized(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    message = "The token is missing or invalid"
    headers = {"WWW-Authenticate": "Bearer"}  # noqa: RUF012 -- read-only class constant


class Forbidden(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "Insufficient rights to perform the operation"


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Resource not found"


class MethodNotAllowed(APIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    code = "METHOD_NOT_ALLOWED"
    message = "Method not allowed"


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "Resource already exists"


class EmailAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    code = "EMAIL_ALREADY_EXISTS"
    message = "User with this email already exists"


class ValidationFailed(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "VALIDATION_FAILED"
    message = "Some fields are not correct."


class Inactive(APIException):
    status_code = status.HTTP_423_LOCKED
    code = "USER_INACTIVE"
    message = "The user has been deactivated"
