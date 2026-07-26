from passlib.hash import argon2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.logger import Logger
from app.core.schemas.user import UserRole
from app.infrastructure.models.user import User


async def create_admin(session: AsyncSession):
    email = settings.ADMIN_EMAIL
    logger = Logger().get_logger()

    stmt = select(User).where(User.email == email)  # noqa
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if admin:
        logger.warning(f"User {email} already exists!")
        return

    new_admin = User(
        email=email,
        password=argon2.hash(settings.ADMIN_PASSWORD),
        fullName=settings.ADMIN_FULLNAME,
        role=UserRole.ADMN,
    )
    session.add(new_admin)

    await session.flush()
    await session.commit()
    await session.refresh(new_admin)

    logger.info(f"Admin {email} successfully created!")
