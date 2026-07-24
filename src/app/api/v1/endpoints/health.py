from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.schemas.responses import PingResponse
from app.infrastructure.database.db_helper import db_helper

router = APIRouter(prefix="", tags=["Health"])


@router.get("/ping", response_model=PingResponse, status_code=status.HTTP_200_OK)
async def ping():
    return PingResponse(status="ok")


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    checks = {}
    all_ready = True

    try:
        async for session in db_helper.session_getter():
            await session.execute(text("SELECT 1"))
            checks["database"] = "ready"
            break
    except Exception as e:
        checks["database"] = "not ready:" + str(e)
        all_ready = False

    if not all_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "checks": checks}
        )

    return {"status": "ready", "checks": checks}
