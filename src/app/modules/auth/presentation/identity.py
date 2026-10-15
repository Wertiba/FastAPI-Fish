from fastapi import Request

from app.modules.auth.application.ports import TokenService
from app.modules.users.public import UsersApi
from app.shared.application.identity import IdentityProvider
from app.shared.domain.errors import AuthenticationError
from app.shared.domain.identity import Identity


class BearerIdentityProvider(IdentityProvider):
    """``Authorization: Bearer <access>`` -> активный пользователь. Кешируется на запрос."""

    def __init__(self, request: Request, tokens: TokenService, users: UsersApi) -> None:
        self._request = request
        self._tokens = tokens
        self._users = users
        self._identity: Identity | None = None

    async def get_identity(self) -> Identity:
        if self._identity is None:
            self._identity = await self._resolve()
        return self._identity

    async def _resolve(self) -> Identity:
        scheme, _, token = self._request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError
        user = await self._users.get_user(self._tokens.read_access_token(token))
        if user is None or not user.is_active:
            raise AuthenticationError
        return Identity(user_id=user.id, role=user.role)
