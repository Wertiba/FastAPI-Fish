from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.uow import UnitOfWorkDep
from app.services import JWTService, UserService


def get_user_service(uow: UnitOfWorkDep) -> UserService:
    jwt_service = JWTService()
    return UserService(uow, jwt_service)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
