from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.session import SessionDep
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService


def get_auth_service(session: SessionDep) -> AuthService:
    uow = UnitOfWork(session)
    jwt_service = JWTService()
    return AuthService(uow, jwt_service)


AuthServiceDep = Annotated["AuthService", Depends(get_auth_service)]
