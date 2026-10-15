from app.modules.users.infrastructure.tables import map_tables
from app.modules.users.ioc import UsersProvider
from app.modules.users.presentation.router import router
from app.shared.module import Module

users_module = Module(
    name="users",
    providers=[UsersProvider()],
    routers=[router],
    map_tables=map_tables,
)
