"""Schema names are part of the API contract: they are the OpenAPI components the frontend generates code from.

Ids are plain ``UUID`` here: the ``UserId`` alias would become a separate OpenAPI component.
"""

from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field

from app.domain.users.enums import UserRole
from app.presentation.http.password import check_len_password
from app.presentation.http.schemas.base import PyModel, UtcDatetime
from app.presentation.http.schemas.token import AccessTokenResponse

Email = Annotated[EmailStr, Field(max_length=254)]
Password = Annotated[str, AfterValidator(check_len_password)]
FullName = Annotated[str, Field(pattern=r"^[а-яА-Яa-zA-Z0-9 _-]{2,200}$")]


class UserRegisterBody(PyModel):
    email: Email
    password: Password
    fullName: FullName


class AdminRegisterUserBody(PyModel):
    email: Email
    password: Password
    fullName: FullName
    role: UserRole = UserRole.USER
    isActive: bool = True


class UserUpdateBody(PyModel):
    fullName: FullName
    role: UserRole | None = None
    isActive: bool | None = None


class UserLoginBody(PyModel):
    email: str
    password: str


class UserReadResponse(PyModel):
    id: UUID
    email: EmailStr
    fullName: str
    role: UserRole
    isActive: bool
    createdAt: UtcDatetime
    updatedAt: UtcDatetime
    createdBy: UUID


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse
