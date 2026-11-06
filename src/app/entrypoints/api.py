"""``api`` process: FastAPI for the website and the mobile app. ``uvicorn app.entrypoints.api:app``."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import MODULES, build_container, error_map
from app.shared.infra.config import HttpConfig, MobileConfig
from app.shared.infra.logger import Logger
from app.shared.presentation.http.errors.handlers import register_exception_handlers
from app.shared.presentation.http.middleware.app_version import AppVersionMiddleware
from app.shared.presentation.http.middleware.observability import ObservabilityMiddleware
from app.shared.presentation.http.middleware.trace_id import TraceIdMiddleware
from app.shared.presentation.http.ops import router as ops_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: AsyncContainer = app.state.dishka_container
    try:
        for module in MODULES:
            if module.on_startup is not None:
                await module.on_startup(container)
        logger.info("application_started")
        yield
    finally:
        await container.close()
        logger.info("application_stopped")


def create_app(container: AsyncContainer | None = None) -> FastAPI:
    if container is None:
        container = build_container()
    http_config = container.get_sync(HttpConfig)
    mobile_config = container.get_sync(MobileConfig)
    container.get_sync(Logger)

    app = FastAPI(lifespan=lifespan)
    setup_dishka(container, app)
    register_exception_handlers(app, error_map())

    origins = [origin.strip() for origin in http_config.cors_allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id", "Location"],
    )

    app.add_middleware(AppVersionMiddleware, min_version=mobile_config.min_app_version)
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(TraceIdMiddleware)

    v1_router = APIRouter(prefix="/api/v1")
    for module in MODULES:
        if module.router is not None:
            v1_router.include_router(module.router)
    app.include_router(ops_router)
    app.include_router(v1_router)
    return app


app = create_app()
