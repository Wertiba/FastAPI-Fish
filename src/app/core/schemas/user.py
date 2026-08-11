from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field

from app.core.enums import UserRole
from app.core.schemas.base import DatetimeResponse, PyModel
from app.core.schemas.token import AccessTokenResponse
from app.core.utils import check_len_password

__all__ = ["UserRole"]


class UserRegisterBody(PyModel):
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[str, AfterValidator(check_len_password)]
    fullName: Annotated[str, Field(min_length=2, max_length=200)]


class UserUpdateBody(PyModel):
    fullName: Annotated[str, Field(min_length=2, max_length=200)]
    role: UserRole | None = None
    isActive: bool | None = None


class UserCreateBody(UserUpdateBody):
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[str, AfterValidator(check_len_password)]
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
    createdBy: UUID | None


class UserReadResponse(UserData, DatetimeResponse):
    pass


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse
