from passlib.hash import argon2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.logger import Logger
from app.infrastructure.models.user import Role, User


async def create_admin(session: AsyncSession):
    email = settings.ADMIN_EMAIL
    logger = Logger().get_logger()

    stmt = select(User).where(User.email == email)  # noqa
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if admin:
        logger.warning(f"User {email} already exists!")
        return

    role_stmt = select(Role).where(Role.code == "ADMN") # noqa
    role_result = await session.execute(role_stmt)
    admin_role = role_result.scalar_one_or_none()

    if not admin_role:
        logger.error("Failed to create or find ADMN role!")
        raise ValueError("Admin role not found after seeding.")

    new_admin = User(
        email=email,
        password=argon2.hash(settings.ADMIN_PASSWORD),
        fullName=settings.ADMIN_FULLNAME,
    )
    new_admin.roles = [admin_role]
    session.add(new_admin)
    await session.flush()

    await session.commit()
    await session.refresh(new_admin)

    logger.info(f"Admin {email} successfully created!")
