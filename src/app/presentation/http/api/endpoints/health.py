from typing import Any

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from app.application.ports.database_health import DatabaseHealth
from app.presentation.http.schemas.responses import PingResponse

router = APIRouter(route_class=DishkaRoute, prefix="/health", tags=["Health"])


@router.get("/liveness", response_model=PingResponse, status_code=status.HTTP_200_OK)
async def liveness() -> PingResponse:
    return PingResponse(status="ok")


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness(response: Response, health: FromDishka[DatabaseHealth]) -> dict[str, Any]:
    try:
        await health.check()
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        # Only the type: the message can carry hosts and credentials.
        return {"status": "not ready", "checks": {"database": f"not ready: {type(exc).__name__}"}}
    return {"status": "ready", "checks": {"database": "ready"}}
