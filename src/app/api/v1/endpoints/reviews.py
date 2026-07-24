from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.dependencies import AnyViewUserDep, ApproverUserDep, ReviewServiceDep
from app.core.schemas.review import ReviewCreateBody, ReviewReadResponse, ReviewResultsResponse

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewReadResponse, status_code=status.HTTP_201_CREATED)
async def create(user_data: ApproverUserDep, review_service: ReviewServiceDep,
                 review_data: ReviewCreateBody) -> ReviewReadResponse | None:
    return await review_service.create(user_data, review_data)


@router.get("/{id}", response_model=ReviewReadResponse, status_code=status.HTTP_200_OK)
async def get_current(_: AnyViewUserDep, id: UUID, review_service: ReviewServiceDep) -> ReviewReadResponse | None:
    return await review_service.get_by_id(id)


@router.get("/all/{code}", response_model=ReviewResultsResponse, status_code=status.HTTP_200_OK)
async def get_all(_: AnyViewUserDep, code: str, review_service: ReviewServiceDep,
                  version: float | None = Query(default=None)) -> ReviewResultsResponse | None:
    return await review_service.get_all(code, version)
