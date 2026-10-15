"""Публичный контракт модуля users.

Другие модули импортируют из ``users`` ТОЛЬКО этот файл
(проверяется тестом ``tests/architecture``). Реализация ``UsersApi`` —
в ``application/public_api.py``, подключается через Dishka.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import EmailStr

from app.shared.application.events import Event
from app.shared.domain.identity import UserRole
from app.shared.presentation.schemas import CamelModel, UtcDatetime


@dataclass(frozen=True, slots=True, kw_only=True)
class UserInfo:
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(Event):
    user_id: UUID


class UsersApi(Protocol):
    async def get_user(self, user_id: UUID) -> UserInfo | None: ...

    async def register(self, *, email: str, password: str, full_name: str) -> UserInfo:
        """Самостоятельная регистрация (роль USER). Не коммитит — это делает вызывающий."""
        ...

    async def authenticate(self, *, email: str, password: str) -> UserInfo:
        """Проверка логина/пароля. Бросает ``AuthenticationError`` или ``UserInactiveError``."""
        ...


# HTTP-представление пользователя. Общее для users и auth, поэтому живёт в контракте:
# в OpenAPI это одна компонента ``UserReadResponse``, а не две похожие.
# (Комментарий, а не docstring: docstring попал бы в description схемы.)
class UserReadResponse(CamelModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime
    created_by: UUID
