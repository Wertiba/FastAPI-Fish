from typing import Annotated

from fastapi import Depends, Query

from app.core.utils.paginated import PaginationParams


def get_pagination(
    page: int = Query(0, ge=0, description="Page number"),
    size: int = Query(10, ge=1, le=1000, description="Page size"),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]
