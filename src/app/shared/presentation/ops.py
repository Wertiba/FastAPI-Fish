"""Служебные эндпоинты вне /api/v1: пробы для оркестратора и метрики."""

from typing import Any

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.shared.presentation.schemas import PingResponse

router = APIRouter(route_class=DishkaRoute)


@router.get("/health/liveness", tags=["Health"], response_model=PingResponse, status_code=status.HTTP_200_OK)
async def liveness() -> PingResponse:
    return PingResponse(status="ok")


@router.get("/health/readiness", tags=["Health"], status_code=status.HTTP_200_OK)
async def readiness(engine: FromDishka[AsyncEngine], response: Response) -> dict[str, Any]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "checks": {"database": f"not ready: {type(exc).__name__}"}}
    return {"status": "ready", "checks": {"database": "ready"}}


@router.get("/metrics", tags=["Metrics"])
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
