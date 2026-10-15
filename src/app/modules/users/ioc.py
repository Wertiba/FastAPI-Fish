from dishka import Provider, Scope, provide, provide_all

from app.modules.users.application.commands import CreateUser, DeactivateUser, EnsureAdmin, UpdateUser
from app.modules.users.application.ports import PasswordHasher, UserRepository
from app.modules.users.application.public_api import UsersApiImpl
from app.modules.users.application.queries import GetCurrentUser, GetUser, ListUsers
from app.modules.users.application.registrar import UserRegistrar
from app.modules.users.infrastructure.password_hasher import Argon2PasswordHasher
from app.modules.users.infrastructure.repository import SqlUserRepository
from app.modules.users.public import UsersApi


class UsersProvider(Provider):
    scope = Scope.REQUEST

    password_hasher = provide(Argon2PasswordHasher, provides=PasswordHasher, scope=Scope.APP)
    repository = provide(SqlUserRepository, provides=UserRepository)
    public_api = provide(UsersApiImpl, provides=UsersApi)

    interactors = provide_all(
        UserRegistrar,
        CreateUser,
        UpdateUser,
        DeactivateUser,
        EnsureAdmin,
        GetUser,
        GetCurrentUser,
        ListUsers,
    )
