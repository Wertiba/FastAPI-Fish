from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.logger import Logger
from app.core.settings import settings
from app.infrastructure.models.user import User
from app.services.jwt_service import JWTService


async def create_admin(session: AsyncSession):
    email = settings.APP_ADMIN_EMAIL
    logger = Logger().get_logger()

    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if admin:
        logger.warning(f"User {email} already exists!")
        return

    new_admin = User(
        email=email,
        password=JWTService().get_password_hash(settings.APP_ADMIN_PASSWORD),
        full_name=settings.APP_ADMIN_FULLNAME,
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(new_admin)

    await session.flush()
    new_admin.created_by = new_admin.id
    await session.commit()
    await session.refresh(new_admin)

    logger.info(f"Admin {email} successfully created!")
