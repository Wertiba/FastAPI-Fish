from datetime import datetime

from fastapi import APIRouter, Query, status

from app.api.v1.dependencies import AnyViewUserDep, EventServiceDep
from app.core.schemas.reports import ExperimentReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{code}", response_model=ExperimentReportResponse, status_code=status.HTTP_200_OK)
async def get_report(_: AnyViewUserDep, event_service: EventServiceDep,
                      code: str, time_from: datetime = Query(),
                      time_to: datetime = Query()) -> ExperimentReportResponse | None:
    return await event_service.get_report(code, time_from, time_to)
