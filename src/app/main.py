"""Фабрика приложения. Запуск: ``uvicorn app.main:create_app --factory``."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bootstrap.config import Settings
from app.bootstrap.ioc import build_container
from app.bootstrap.logging import setup_logging
from app.modules.registry import MODULES
from app.modules.users.application.commands import EnsureAdmin
from app.shared.infrastructure.database import metadata
from app.shared.module import Module
from app.shared.presentation.errors import setup_error_handlers
from app.shared.presentation.ops import router as ops_router
from app.shared.presentation.request_context import RequestContextMiddleware

API_PREFIX = "/api/v1"


async def _on_startup(container: AsyncContainer, settings: Settings) -> None:
    if settings.db_create_tables:
        engine = await container.get(AsyncEngine)
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    if settings.admin_email and settings.admin_password:
        async with container() as request_container:
            ensure_admin = await request_container.get(EnsureAdmin)
            await ensure_admin(
                email=settings.admin_email,
                password=settings.admin_password,
                full_name=settings.admin_full_name,
            )


def create_app(settings: Settings | None = None, modules: Sequence[Module] = MODULES) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]  # значения берутся из env
    setup_logging(settings.log_level, settings.log_file)

    for module in modules:
        if module.map_tables:
            module.map_tables()
    container = build_container(settings, modules)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await _on_startup(container, settings)
        yield
        await container.close()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id", "Location"],
    )
    app.add_middleware(RequestContextMiddleware)
    setup_error_handlers(app)

    app.include_router(ops_router)
    for module in modules:
        for router in module.routers:
            app.include_router(router, prefix=API_PREFIX)

    setup_dishka(container, app)
    return app
