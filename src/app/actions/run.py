import asyncio

from app.actions.first_admin import create_admin
from app.infrastructure.database.db_helper import db_helper


async def run():
    async with db_helper.session_factory() as session:
        await create_admin(session)


if __name__ == '__main__':
    asyncio.run(run())
