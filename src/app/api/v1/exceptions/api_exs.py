from fastapi import status

from app.api.v1.exceptions.base import APIException


class BadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    message = "Invalid request"


class Unauthorized(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    message = "The token is missing or invalid"


class Forbidden(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "Insufficient rights to perform the operation"


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Resource not found"


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "Data conflict"


class ValidationFailed(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_FAILED"
    message = "Some fields are not correct."


class Inactive(APIException):
    status_code = status.HTTP_423_LOCKED
    code = "USER_INACTIVE"
    message = "The user has been deactivated"
