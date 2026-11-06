"""Inputs of the user use cases; they are the request bodies too.

Class names are part of the API contract: they are the OpenAPI components the frontend generates code from.
"""

from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field

from app.application.schema import PyModel
from app.application.users.password import check_len_password
from app.domain.users.enums import UserRole

Email = Annotated[EmailStr, Field(max_length=254)]
Password = Annotated[str, AfterValidator(check_len_password)]
FullName = Annotated[str, Field(pattern=r"^[а-яА-Яa-zA-Z0-9 _-]{2,200}$")]


class UserRegisterBody(PyModel):
    email: Email
    password: Password
    full_name: FullName


class AdminRegisterUserBody(PyModel):
    email: Email
    password: Password
    full_name: FullName
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserUpdateBody(PyModel):
    full_name: FullName
    role: UserRole | None = None
    is_active: bool | None = None


class UserLoginBody(PyModel):
    email: str
    password: str
