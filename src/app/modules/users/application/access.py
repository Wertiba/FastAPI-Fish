from app.modules.users.application.ports import UserGateway
from app.modules.users.domain.enums import UserRole
from app.shared.domain.errors import ForbiddenError
from app.shared.domain.ids import UserId


async def is_admin(user_gateway: UserGateway, user_id: UserId) -> bool:
    """The role is read from the database, so revoking it takes effect before the access token expires."""
    user = await user_gateway.get_by_id(user_id)
    return user is not None and user.role == UserRole.ADMIN


async def require_admin(user_gateway: UserGateway, user_id: UserId) -> None:
    if not await is_admin(user_gateway, user_id):
        raise ForbiddenError


async def require_admin_or_self(user_gateway: UserGateway, user_id: UserId, target_id: UserId) -> None:
    if user_id != target_id:
        await require_admin(user_gateway, user_id)
