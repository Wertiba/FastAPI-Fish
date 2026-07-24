from fastapi import APIRouter, status

from app.api.v1.dependencies import EventServiceDep
from app.core.schemas.event import EventBatchBody, EventBatchResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventBatchResponse, status_code=status.HTTP_207_MULTI_STATUS)
async def process_batch(data: EventBatchBody, event_service: EventServiceDep) -> EventBatchResponse:
    return await event_service.process_batch(data)
