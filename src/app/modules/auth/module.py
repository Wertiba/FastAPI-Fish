from app.modules.auth.application.event_handlers import RevokeSessionsOnUserDeactivated
from app.modules.auth.infrastructure.tables import map_tables
from app.modules.auth.ioc import AuthProvider
from app.modules.auth.presentation.router import router
from app.modules.users.public import UserDeactivated
from app.shared.module import Module

auth_module = Module(
    name="auth",
    providers=[AuthProvider()],
    routers=[router],
    map_tables=map_tables,
    subscriptions={UserDeactivated: [RevokeSessionsOnUserDeactivated]},
)
