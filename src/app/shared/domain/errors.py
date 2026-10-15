"""Базовые ошибки предметной области.

Каждый модуль наследует свои ошибки от одной из категорий ниже.
Категория определяет HTTP-статус (см. ``shared/presentation/errors.py``),
а ``code``/``default_message`` — то, что увидит клиент.
"""

from typing import Any, ClassVar


class DomainError(Exception):
    code: ClassVar[str] = "DOMAIN_ERROR"
    default_message: ClassVar[str] = "Domain error"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    default_message = "Resource not found"


class ConflictError(DomainError):
    code = "CONFLICT"
    default_message = "Resource already exists"


class AuthenticationError(DomainError):
    code = "UNAUTHORIZED"
    default_message = "The token is missing or invalid"


class AccessDeniedError(DomainError):
    code = "FORBIDDEN"
    default_message = "Insufficient rights to perform the operation"


class BusinessRuleError(DomainError):
    code = "VALIDATION_FAILED"
    default_message = "Some fields are not correct."


class LockedError(DomainError):
    code = "LOCKED"
    default_message = "Resource is locked"
