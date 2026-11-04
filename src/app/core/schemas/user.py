import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field

from app.core.enums import UserRole
from app.core.schemas.base import DatetimeResponse, PyModel
from app.core.schemas.token import AccessTokenResponse

__all__ = ["UserRole"]


def check_password(password: str) -> str:
    if not (8 <= len(password) <= 72):
        raise ValueError("Password must be between 8 and 72 characters")

    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    return password


class UserRegisterBody(PyModel):
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[str, AfterValidator(check_password)]
    fullName: Annotated[str, Field(pattern=r"^[а-яА-Яa-zA-Z0-9 _-]{2,200}$")]


class UserUpdateBody(PyModel):
    fullName: Annotated[str, Field(pattern=r"^[а-яА-Яa-zA-Z0-9 _-]{2,200}$")]
    role: UserRole | None = None
    isActive: bool | None = None


class AdminRegisterUserBody(UserRegisterBody):
    role: UserRole = UserRole.USER
    isActive: bool = True


class UserLoginBody(PyModel):
    email: str
    password: str


class UserData(PyModel):
    id: UUID
    email: EmailStr
    fullName: str
    role: UserRole
    isActive: bool

    createdAt: datetime
    updatedAt: datetime
    createdBy: UUID


class UserReadResponse(UserData, DatetimeResponse):
    pass


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse


class UserFilterQuery(PyModel):
    email: str | None = None
    fullName: str | None = None
    role: UserRole | None = None
    isActive: bool | None = None
    createdFrom: datetime | None = None
    createdTo: datetime | None = None
