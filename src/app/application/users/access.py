from uuid import UUID

from app.application.ports.user_gateway import UserGateway
from app.domain.users.enums import UserRole
from app.domain.users.errors import ForbiddenError


async def is_admin(user_gateway: UserGateway, user_id: UUID) -> bool:
    """The role is read from the database, so revoking it takes effect before the access token expires."""
    user = await user_gateway.get_by_id(user_id)
    return user is not None and user.role == UserRole.ADMIN


async def require_admin(user_gateway: UserGateway, user_id: UUID) -> None:
    if not await is_admin(user_gateway, user_id):
        raise ForbiddenError


async def require_admin_or_self(user_gateway: UserGateway, user_id: UUID, target_id: UUID) -> None:
    if user_id != target_id:
        await require_admin(user_gateway, user_id)
