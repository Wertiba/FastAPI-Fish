import asyncio

from app.actions.create_base_events import create_base_events
from app.actions.create_base_links import create_base_links
from app.actions.create_base_metrics import create_base_metrics
from app.actions.create_roles import seed_roles
from app.actions.first_admin import create_admin
from app.infrastructure.database.db_helper import db_helper


async def run():
    async with db_helper.session_factory() as session:
        await seed_roles(session)
        await create_admin(session)
        await create_base_metrics(session)
        await create_base_events(session)
        await create_base_links(session)


if __name__ == '__main__':
    asyncio.run(run())
