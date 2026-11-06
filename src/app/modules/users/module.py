"""Composition of the ``users`` module: the only file that wires its layers together."""

from dishka import AsyncContainer, Provider, Scope, provide, provide_all

from app.modules.users.api.contracts import UsersFacade
from app.modules.users.application.facade import UsersFacadeImpl
from app.modules.users.application.interactors import (
    CreateUser,
    DeactivateUser,
    EnsureAdmin,
    GetMe,
    GetUser,
    ListUsers,
    UpdateUser,
)
from app.modules.users.application.ports import PasswordHasher, UserGateway
from app.modules.users.infra.gateway import SqlAlchemyUserGateway
from app.modules.users.infra.password_hasher import Argon2PasswordHasher
from app.modules.users.presentation.http.errors import USERS_ERRORS
from app.modules.users.presentation.http.router import router
from app.shared.infra.config import AdminConfig
from app.shared.module import Module


class UsersProvider(Provider):
    scope = Scope.REQUEST

    password_hasher = provide(Argon2PasswordHasher, provides=PasswordHasher, scope=Scope.APP)
    gateway = provide(SqlAlchemyUserGateway, provides=UserGateway)
    facade = provide(UsersFacadeImpl, provides=UsersFacade)
    interactors = provide_all(ListUsers, GetUser, GetMe, CreateUser, UpdateUser, DeactivateUser, EnsureAdmin)


async def ensure_admin(container: AsyncContainer) -> None:
    config = await container.get(AdminConfig)
    if not (config.email and config.password):
        return
    async with container() as request_container:
        ensure = await request_container.get(EnsureAdmin)
        await ensure(email=config.email, password=config.password, full_name=config.full_name)


users_module = Module(
    name="users",
    provider=UsersProvider,
    router=router,
    errors=USERS_ERRORS,
    on_startup=ensure_admin,
)
