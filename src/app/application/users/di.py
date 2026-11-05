from dishka import Provider, Scope, provide_all

from app.application.users.interactors import (
    CreateUser,
    DeactivateUser,
    EnsureAdmin,
    GetMe,
    GetUser,
    ListUsers,
    UpdateUser,
)


class UserProvider(Provider):
    scope = Scope.REQUEST
    interactors = provide_all(ListUsers, GetUser, GetMe, CreateUser, UpdateUser, DeactivateUser, EnsureAdmin)
