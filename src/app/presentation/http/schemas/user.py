"""Response schemas; the request bodies are the use case inputs in ``app.application.users.schemas``.

Class names are part of the API contract: they are the OpenAPI components the frontend generates code from.
"""

from uuid import UUID

from pydantic import EmailStr

from app.application.schema import PyModel
from app.domain.users.enums import UserRole
from app.presentation.http.schemas.base import UtcDatetime
from app.presentation.http.schemas.token import AccessTokenResponse


class UserReadResponse(PyModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime
    created_by: UUID


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse
