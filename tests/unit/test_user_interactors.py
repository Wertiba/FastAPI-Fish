"""Interactors are tested without a database or HTTP, on fakes of their ports."""

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.modules.users.api.contracts import UserDeactivated
from app.modules.users.application.dto import UserUpdateData
from app.modules.users.application.interactors import DeactivateUser, UpdateUser
from app.modules.users.application.ports import UserCriteria
from app.modules.users.domain.entity import User
from app.modules.users.domain.enums import UserRole
from app.modules.users.domain.errors import UserNotFoundError
from app.shared.application.events import Event
from app.shared.domain.errors import ForbiddenError


def make_user(role: UserRole = UserRole.USER) -> User:
    return User(email=f"{uuid4().hex}@example.com", password_hash="h", full_name="U", role=role)


class InMemoryUsers:
    def __init__(self, *users: User) -> None:
        self.items = {user.id: user for user in users}

    async def get_by_id(self, id_: UUID) -> User | None:
        return self.items.get(id_)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.items.values() if user.email == email), None)

    async def get_all(self, offset: int, limit: int, criteria: UserCriteria) -> list[User]:
        return list(self.items.values())[offset : offset + limit]

    async def count(self, criteria: UserCriteria) -> int:
        return len(self.items)


class RecordingEvents:
    def __init__(self) -> None:
        self.published: list[Event] = []

    async def publish(self, event: Event) -> None:
        self.published.append(event)

    @property
    def deactivated(self) -> list[UUID]:
        return [event.user_id for event in self.published if isinstance(event, UserDeactivated)]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    async def add(self, entity: Any) -> None:
        pass

    async def delete(self, entity: Any) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True


class Context:
    def __init__(self, *users: User) -> None:
        self.uow = FakeUnitOfWork()
        self.users = InMemoryUsers(*users)
        self.events = RecordingEvents()

    def build[T](self, interactor: type[T]) -> T:
        return interactor(self.uow, self.users, None, self.events)  # type: ignore[call-arg]


class TestUpdateUser:
    async def test_user_renames_self(self) -> None:
        user = make_user()
        ctx = Context(user)

        result = await ctx.build(UpdateUser)(user.id, user.id, UserUpdateData(fullName="New"))

        assert result.fullName == user.full_name == "New"
        assert ctx.uow.committed
        assert ctx.events.deactivated == []

    @pytest.mark.parametrize(
        "data",
        [
            UserUpdateData(fullName="X", role=UserRole.ADMIN),
            UserUpdateData(fullName="X", isActive=False),
        ],
    )
    async def test_user_cannot_change_own_role_or_status(self, data: UserUpdateData) -> None:
        user = make_user()
        ctx = Context(user)

        with pytest.raises(ForbiddenError):
            await ctx.build(UpdateUser)(user.id, user.id, data)
        assert user.role is UserRole.USER
        assert user.is_active

    async def test_sending_current_values_is_allowed_for_user(self) -> None:
        user = make_user()
        data = UserUpdateData(fullName="X", role=UserRole.USER, isActive=True)

        await Context(user).build(UpdateUser)(user.id, user.id, data)

    async def test_user_cannot_update_others(self) -> None:
        alice, bob = make_user(), make_user()
        with pytest.raises(ForbiddenError):
            await Context(alice, bob).build(UpdateUser)(alice.id, bob.id, UserUpdateData(fullName="X"))

    async def test_admin_deactivation_publishes_event(self) -> None:
        admin, user = make_user(UserRole.ADMIN), make_user()
        ctx = Context(admin, user)

        await ctx.build(UpdateUser)(admin.id, user.id, UserUpdateData(fullName="X", isActive=False))

        assert user.is_active is False
        assert ctx.events.deactivated == [user.id]


class TestDeactivateUser:
    async def test_deactivates_and_publishes_event(self) -> None:
        admin, user = make_user(UserRole.ADMIN), make_user()
        ctx = Context(admin, user)

        await ctx.build(DeactivateUser)(admin.id, user.id)

        assert user.is_active is False
        assert ctx.events.deactivated == [user.id]
        assert ctx.uow.committed

    async def test_requires_admin(self) -> None:
        actor, user = make_user(), make_user()
        with pytest.raises(ForbiddenError):
            await Context(actor, user).build(DeactivateUser)(actor.id, user.id)

    async def test_unknown_user(self) -> None:
        admin = make_user(UserRole.ADMIN)
        with pytest.raises(UserNotFoundError):
            await Context(admin).build(DeactivateUser)(admin.id, uuid4())
