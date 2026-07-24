from sqlalchemy import select

from app.core.logger import Logger
from app.infrastructure.models import Role


async def seed_roles(session):
    logger = Logger().get_logger()
    default_roles = [
        {"code": "VIEW", "value": "Viewer", "description": "Может просматривать данные"},
        {"code": "APPR", "value": "Approver", "description": "Может утверждать изменения"},
        {"code": "EXPR", "value": "Experimenter", "description": "Может создавать эксперименты"},
        {"code": "ADMN", "value": "Admin", "description": "Полный доступ к системе"},
    ]

    for role_data in default_roles:
        stmt = select(Role).where(Role.code == role_data["code"])   # noqa
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            role = Role(**role_data)
            session.add(role)

    await session.commit()
    logger.info("All roles created successfully!")
