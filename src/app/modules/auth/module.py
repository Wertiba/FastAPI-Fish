"""Composition of the ``auth`` module: the only file that wires its layers together."""

from datetime import timedelta

from dishka import Provider, Scope, provide, provide_all

from app.modules.auth.application.handlers import RevokeSessionsOnUserDeactivated
from app.modules.auth.application.identity import TokenIdentityProvider
from app.modules.auth.application.interactors import LoginUser, Logout, RefreshTokens, RegisterUser
from app.modules.auth.application.jobs import CleanupExpiredRefreshTokens
from app.modules.auth.application.ports import RefreshTokenGateway, TokenService
from app.modules.auth.infra.gateway import SqlAlchemyRefreshTokenGateway
from app.modules.auth.infra.jwt_service import JWTService
from app.modules.auth.presentation.http.errors import AUTH_ERRORS
from app.modules.auth.presentation.http.router import router
from app.modules.users.api.contracts import UserDeactivated
from app.shared.application.jobs import JobSpec
from app.shared.application.ports.identity import IdentityProvider
from app.shared.module import Module


class AuthProvider(Provider):
    scope = Scope.REQUEST

    tokens = provide(JWTService, provides=TokenService, scope=Scope.APP)
    gateway = provide(SqlAlchemyRefreshTokenGateway, provides=RefreshTokenGateway)
    identity = provide(TokenIdentityProvider, provides=IdentityProvider)
    interactors = provide_all(RegisterUser, LoginUser, RefreshTokens, Logout)
    handlers = provide_all(RevokeSessionsOnUserDeactivated)
    jobs = provide_all(CleanupExpiredRefreshTokens)


auth_module = Module(
    name="auth",
    provider=AuthProvider,
    router=router,
    errors=AUTH_ERRORS,
    subscriptions={UserDeactivated: [RevokeSessionsOnUserDeactivated]},
    jobs=[
        JobSpec(name="auth.cleanup_expired_refresh_tokens", job=CleanupExpiredRefreshTokens, every=timedelta(hours=1))
    ],
)
