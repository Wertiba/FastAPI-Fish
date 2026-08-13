from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.actions.first_admin import create_admin
from app.api import ops_router, v1_router
from app.api.v1.exceptions.handlers import register_exception_handlers
from app.core.config import settings
from app.core.logger import Logger
from app.core.middleware.trace_id import TraceIdMiddleware
from app.infrastructure.database.db_helper import db_helper

logger = Logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_helper.session_factory() as session:
        await create_admin(session)
    yield


app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)

_DEFAULT_CORS_ORIGINS = "http://localhost,http://localhost:8080"
origins = [
    origin.strip()
    for origin in settings.get("APP_CORS_ALLOWED_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TraceIdMiddleware)

app.include_router(ops_router)
app.include_router(v1_router, prefix="/api")
