from passlib.hash import argon2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import UserRole
from app.core.logger import Logger
from app.infrastructure.models.user import User


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
        password=argon2.hash(settings.APP_ADMIN_PASSWORD),
        full_name=settings.APP_ADMIN_FULLNAME,
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(new_admin)

    await session.flush()
    await session.commit()
    await session.refresh(new_admin)

    logger.info(f"Admin {email} successfully created!")
