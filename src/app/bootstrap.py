from dishka import AsyncContainer, Provider, make_async_container

from app.application.auth.di import AuthProvider
from app.application.users.di import UserProvider
from app.infra.database.di import DatabaseProvider
from app.infra.di import ConfigProvider
from app.infra.gateways.di import GatewayProvider
from app.infra.security.di import SecurityProvider


def build_container(*providers: Provider) -> AsyncContainer:
    """Extra ``providers`` go last, so tests can override any dependency with ``override=True``."""
    return make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        GatewayProvider(),
        SecurityProvider(),
        AuthProvider(),
        UserProvider(),
        *providers,
    )
