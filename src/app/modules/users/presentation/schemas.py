"""Имена схем совпадают с FastAPI-Fish: в OpenAPI это имена компонент для кодогенерации на фронте."""

from app.modules.users.public import UserReadResponse
from app.shared.domain.identity import UserRole
from app.shared.presentation.fields import Email, FullName, Password
from app.shared.presentation.schemas import CamelModel

__all__ = ["AdminRegisterUserBody", "UserReadResponse", "UserUpdateBody"]


class AdminRegisterUserBody(CamelModel):
    email: Email
    password: Password
    full_name: FullName
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserUpdateBody(CamelModel):
    full_name: FullName
    role: UserRole | None = None
    is_active: bool | None = None
