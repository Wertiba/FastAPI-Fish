import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.users.interactors import EnsureAdmin
from app.bootstrap import build_container
from app.infra.config import AdminConfig, HttpConfig
from app.infra.logger import Logger
from app.presentation.http.api import ops_router, v1_router
from app.presentation.http.api.v1.exceptions.handlers import register_exception_handlers
from app.presentation.http.middleware.observability import ObservabilityMiddleware
from app.presentation.http.middleware.trace_id import TraceIdMiddleware

logger = logging.getLogger(__name__)


async def _ensure_admin(container: AsyncContainer) -> None:
    config = await container.get(AdminConfig)
    if not (config.email and config.password):
        return
    async with container() as request_container:
        ensure_admin = await request_container.get(EnsureAdmin)
        await ensure_admin(email=config.email, password=config.password, full_name=config.full_name)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: AsyncContainer = app.state.dishka_container
    try:
        await _ensure_admin(container)
        logger.info("application_started")
        yield
    finally:
        await container.close()
        logger.info("application_stopped")


def create_app(container: AsyncContainer | None = None) -> FastAPI:
    if container is None:
        container = build_container()
    http_config = container.get_sync(HttpConfig)
    container.get_sync(Logger)

    app = FastAPI(lifespan=lifespan)
    setup_dishka(container, app)
    register_exception_handlers(app)

    origins = [origin.strip() for origin in http_config.cors_allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id", "Location"],
    )

    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(TraceIdMiddleware)

    app.include_router(ops_router)
    app.include_router(v1_router, prefix="/api")
    return app


app = create_app()
