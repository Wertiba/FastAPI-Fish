from dataclasses import dataclass
from uuid import UUID

from app.modules.auth.application.ports import RefreshTokenRepository, TokenService
from app.modules.auth.domain.entities import RefreshToken
from app.modules.users.public import UserInfo, UsersApi
from app.shared.application.transaction import TransactionManager
from app.shared.domain.errors import AuthenticationError


@dataclass(frozen=True, slots=True, kw_only=True)
class IssuedTokens:
    access_token: str
    access_expires_in: int
    refresh_token: str
    refresh_expires_in: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthSession:
    user: UserInfo
    tokens: IssuedTokens


class TokenIssuer:
    """Выпускает пару access/refresh и сохраняет хеш refresh-токена."""

    def __init__(self, tokens: TokenService, refresh_tokens: RefreshTokenRepository) -> None:
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens

    async def issue(self, user_id: UUID) -> IssuedTokens:
        refresh = self._tokens.create_refresh_token(user_id)
        await self._refresh_tokens.add(
            RefreshToken.issue(
                user_id=user_id,
                token_hash=self._tokens.hash_token(refresh),
                ttl_seconds=self._tokens.refresh_ttl,
            )
        )
        return IssuedTokens(
            access_token=self._tokens.create_access_token(user_id),
            access_expires_in=self._tokens.access_ttl,
            refresh_token=refresh,
            refresh_expires_in=self._tokens.refresh_ttl,
        )


class Register:
    def __init__(self, users: UsersApi, issuer: TokenIssuer, tx: TransactionManager) -> None:
        self._users = users
        self._issuer = issuer
        self._tx = tx

    async def __call__(self, *, email: str, password: str, full_name: str) -> AuthSession:
        user = await self._users.register(email=email, password=password, full_name=full_name)
        tokens = await self._issuer.issue(user.id)
        await self._tx.commit()
        return AuthSession(user=user, tokens=tokens)


class Login:
    def __init__(self, users: UsersApi, issuer: TokenIssuer, tx: TransactionManager) -> None:
        self._users = users
        self._issuer = issuer
        self._tx = tx

    async def __call__(self, *, email: str, password: str) -> AuthSession:
        user = await self._users.authenticate(email=email, password=password)
        tokens = await self._issuer.issue(user.id)
        await self._tx.commit()
        return AuthSession(user=user, tokens=tokens)


class RefreshSession:
    """Ротация: старый refresh-токен удаляется, выдаётся новая пара."""

    def __init__(
        self,
        users: UsersApi,
        tokens: TokenService,
        refresh_tokens: RefreshTokenRepository,
        issuer: TokenIssuer,
        tx: TransactionManager,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens
        self._issuer = issuer
        self._tx = tx

    async def __call__(self, raw_refresh_token: str | None) -> IssuedTokens:
        if not raw_refresh_token:
            raise AuthenticationError
        user_id = self._tokens.read_refresh_token(raw_refresh_token)
        token_hash = self._tokens.hash_token(raw_refresh_token)

        stored = await self._refresh_tokens.get(user_id, token_hash)
        if stored is None or stored.is_expired():
            raise AuthenticationError
        user = await self._users.get_user(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError

        await self._refresh_tokens.delete_by_hash(token_hash)
        tokens = await self._issuer.issue(user_id)
        await self._tx.commit()
        return tokens


class Logout:
    def __init__(
        self, tokens: TokenService, refresh_tokens: RefreshTokenRepository, tx: TransactionManager
    ) -> None:
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens
        self._tx = tx

    async def __call__(self, raw_refresh_token: str | None) -> None:
        if not raw_refresh_token:
            raise AuthenticationError
        await self._refresh_tokens.delete_by_hash(self._tokens.hash_token(raw_refresh_token))
        await self._tx.commit()
