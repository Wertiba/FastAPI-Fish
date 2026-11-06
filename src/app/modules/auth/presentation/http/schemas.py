"""Schema names are part of the API contract: they are the OpenAPI components the frontend generates code from."""

from app.modules.users.api.http import Email, FullName, Password, UserReadResponse
from app.shared.presentation.http.schemas.base import PyModel


class UserRegisterBody(PyModel):
    email: Email
    password: Password
    fullName: FullName


class UserLoginBody(PyModel):
    email: str
    password: str


class AccessTokenResponse(PyModel):
    accessToken: str
    expiresIn: int


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse
