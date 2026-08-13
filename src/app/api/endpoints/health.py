from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.schemas.responses import PingResponse
from app.infrastructure.database.db_helper import db_helper

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/liveness", response_model=PingResponse, status_code=status.HTTP_200_OK)
async def liveness() -> PingResponse:
    return PingResponse(status="ok")


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness(response: Response) -> dict:
    checks = {}
    try:
        async for session in db_helper.session_getter():
            await session.execute(text("SELECT 1"))
            checks["database"] = "ready"
            break
    except Exception as e:
        checks["database"] = f"not ready: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "checks": checks}

    return {"status": "ready", "checks": checks}
