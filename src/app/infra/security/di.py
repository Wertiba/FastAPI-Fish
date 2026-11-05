from dishka import Provider, Scope, provide

from app.application.ports.tokens import TokenService
from app.infra.security.jwt_service import JWTService


class SecurityProvider(Provider):
    tokens = provide(JWTService, provides=TokenService, scope=Scope.APP)
