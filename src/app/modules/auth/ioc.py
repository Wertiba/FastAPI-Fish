from dishka import Provider, Scope, provide, provide_all

from app.modules.auth.application.commands import Login, Logout, RefreshSession, Register, TokenIssuer
from app.modules.auth.application.event_handlers import RevokeSessionsOnUserDeactivated
from app.modules.auth.application.ports import RefreshTokenRepository, TokenService
from app.modules.auth.infrastructure.jwt_tokens import JwtTokenService
from app.modules.auth.infrastructure.repository import SqlRefreshTokenRepository
from app.modules.auth.presentation.identity import BearerIdentityProvider
from app.shared.application.identity import IdentityProvider


class AuthProvider(Provider):
    scope = Scope.REQUEST

    token_service = provide(JwtTokenService, provides=TokenService, scope=Scope.APP)
    repository = provide(SqlRefreshTokenRepository, provides=RefreshTokenRepository)
    identity = provide(BearerIdentityProvider, provides=IdentityProvider)

    interactors = provide_all(TokenIssuer, Register, Login, RefreshSession, Logout)
    event_handlers = provide_all(RevokeSessionsOnUserDeactivated)
