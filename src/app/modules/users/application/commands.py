"""Команды: меняют состояние и коммитят транзакцию."""

from uuid import UUID

from loguru import logger

from app.modules.users.application.ports import UserRepository
from app.modules.users.application.registrar import UserRegistrar
from app.modules.users.domain.entities import User
from app.modules.users.domain.errors import UserNotFoundError
from app.modules.users.public import UserDeactivated
from app.shared.application.events import EventPublisher
from app.shared.application.identity import IdentityProvider
from app.shared.application.transaction import TransactionManager
from app.shared.domain.identity import UserRole


class CreateUser:
    def __init__(self, idp: IdentityProvider, registrar: UserRegistrar, tx: TransactionManager) -> None:
        self._idp = idp
        self._registrar = registrar
        self._tx = tx

    async def __call__(
        self, *, email: str, password: str, full_name: str, role: UserRole, is_active: bool
    ) -> User:
        actor = await self._idp.get_identity()
        actor.require_admin()
        user = await self._registrar.register(
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            is_active=is_active,
            created_by=actor.user_id,
        )
        await self._tx.commit()
        return user


class UpdateUser:
    def __init__(
        self,
        idp: IdentityProvider,
        users: UserRepository,
        events: EventPublisher,
        tx: TransactionManager,
    ) -> None:
        self._idp = idp
        self._users = users
        self._events = events
        self._tx = tx

    async def __call__(
        self, user_id: UUID, *, full_name: str, role: UserRole | None, is_active: bool | None
    ) -> User:
        actor = await self._idp.get_identity()
        actor.require_admin_or_self(user_id)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        deactivated = user.update(full_name=full_name, role=role, is_active=is_active, actor=actor)
        if deactivated:
            await self._events.publish(UserDeactivated(user_id=user.id))
        await self._tx.commit()
        return user


class DeactivateUser:
    def __init__(
        self,
        idp: IdentityProvider,
        users: UserRepository,
        events: EventPublisher,
        tx: TransactionManager,
    ) -> None:
        self._idp = idp
        self._users = users
        self._events = events
        self._tx = tx

    async def __call__(self, user_id: UUID) -> None:
        (await self._idp.get_identity()).require_admin()
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        user.deactivate()
        await self._events.publish(UserDeactivated(user_id=user.id))
        await self._tx.commit()


class EnsureAdmin:
    """Создаёт администратора при старте, если его ещё нет (идемпотентно)."""

    def __init__(self, users: UserRepository, registrar: UserRegistrar, tx: TransactionManager) -> None:
        self._users = users
        self._registrar = registrar
        self._tx = tx

    async def __call__(self, *, email: str, password: str, full_name: str) -> None:
        if await self._users.get_by_email(email) is not None:
            logger.info("Admin {} already exists", email)
            return
        await self._registrar.register(
            email=email, password=password, full_name=full_name, role=UserRole.ADMIN
        )
        await self._tx.commit()
        logger.info("Admin {} created", email)
