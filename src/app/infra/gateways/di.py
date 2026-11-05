from dishka import Provider, Scope, provide

from app.application.ports.refresh_token_gateway import RefreshTokenGateway
from app.application.ports.user_gateway import UserGateway
from app.infra.gateways.refresh_token import SqlAlchemyRefreshTokenGateway
from app.infra.gateways.user import SqlAlchemyUserGateway


class GatewayProvider(Provider):
    scope = Scope.REQUEST
    user = provide(SqlAlchemyUserGateway, provides=UserGateway)
    refresh_token = provide(SqlAlchemyRefreshTokenGateway, provides=RefreshTokenGateway)
