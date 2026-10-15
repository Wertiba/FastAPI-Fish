"""Общие FastAPI-зависимости для роутеров модулей."""

from typing import Annotated

from fastapi import Depends, Query, Security
from fastapi.params import Depends as DependsParam
from fastapi.security import HTTPBearer

from app.shared.application.pagination import Pagination


def _pagination(
    page: int = Query(0, ge=0, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
) -> Pagination:
    return Pagination(page=page, size=size)


PaginationQuery = Annotated[Pagination, Depends(_pagination)]

# Только для OpenAPI: добавляет кнопку Authorize в Swagger. Саму проверку
# токена делает IdentityProvider внутри интеракторов.
_bearer = HTTPBearer(auto_error=False, description="Access token из /auth/login")
BEARER_AUTH: list[DependsParam] = [Security(_bearer)]
