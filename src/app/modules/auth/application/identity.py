from dataclasses import dataclass

from app.modules.auth.application.interactors import token_subject
from app.modules.auth.application.ports import ACCESS_TOKEN_TYPE, TokenService
from app.modules.users.api.contracts import UsersFacade
from app.shared.application.ports.identity import CurrentUser, IdentityProvider
from app.shared.domain.errors import InvalidCredentialsError


@dataclass
class TokenIdentityProvider(IdentityProvider):
    """``auth``'s implementation of the shared ``IdentityProvider`` port: access token -> active user."""

    users: UsersFacade
    tokens: TokenService

    async def authenticate(self, access_token: str) -> CurrentUser:
        payload = self.tokens.decode_token(access_token, expected_type=ACCESS_TOKEN_TYPE)
        user = await self.users.get(token_subject(payload))
        if user is None or not user.isActive:
            raise InvalidCredentialsError
        return CurrentUser(id=user.id)
