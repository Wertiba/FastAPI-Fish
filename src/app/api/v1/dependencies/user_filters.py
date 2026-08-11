from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query

from app.core.enums import UserRole
from app.core.schemas.user import UserFilterQuery


def get_user_filters(
    email: str | None = Query(None),
    fullName: str | None = Query(None),
    role: UserRole | None = Query(None),
    isActive: bool | None = Query(None),
    createdFrom: datetime | None = Query(None),
    createdTo: datetime | None = Query(None),
) -> UserFilterQuery:
    return UserFilterQuery(
        email=email,
        fullName=fullName,
        role=role,
        isActive=isActive,
        createdFrom=createdFrom,
        createdTo=createdTo,
    )


UserFilterDep = Annotated[UserFilterQuery, Depends(get_user_filters)]
