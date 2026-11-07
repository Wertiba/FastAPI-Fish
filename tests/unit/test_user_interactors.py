"""Interactors are tested without a database or HTTP, on fakes of their ports."""

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.application.ports.user_gateway import UserCriteria
from app.application.users.interactors import DeactivateUser, UpdateUser
from app.application.users.schemas import UserUpdateBody
from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.entity import User
from app.domain.users.enums import UserRole
from app.domain.users.errors import ForbiddenError, UserNotFoundError


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


class InMemoryRefreshTokens:
    def __init__(self) -> None:
        self.revoked: list[UUID] = []

    async def get_by_user_and_hash(self, user_id: UUID, token_hash: str) -> RefreshToken | None:
        return None

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return None

    async def delete_by_user(self, user_id: UUID) -> None:
        self.revoked.append(user_id)


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
        self.tokens = InMemoryRefreshTokens()

    def build[T](self, interactor: type[T]) -> T:
        return interactor(self.uow, self.users, self.tokens, None)  # type: ignore[call-arg]


class TestUpdateUser:
    async def test_user_renames_self(self) -> None:
        user = make_user()
        ctx = Context(user)

        result = await ctx.build(UpdateUser)(user.id, user.id, UserUpdateBody(full_name="New"))

        assert result.full_name == user.full_name == "New"
        assert ctx.uow.committed
        assert ctx.tokens.revoked == []

    @pytest.mark.parametrize(
        "data",
        [
            UserUpdateBody(full_name="Xx", role=UserRole.ADMIN),
            UserUpdateBody(full_name="Xx", is_active=False),
        ],
    )
    async def test_user_cannot_change_own_role_or_status(self, data: UserUpdateBody) -> None:
        user = make_user()
        ctx = Context(user)

        with pytest.raises(ForbiddenError):
            await ctx.build(UpdateUser)(user.id, user.id, data)
        assert user.role is UserRole.USER
        assert user.is_active

    async def test_sending_current_values_is_allowed_for_user(self) -> None:
        user = make_user()
        data = UserUpdateBody(full_name="Xx", role=UserRole.USER, is_active=True)

        await Context(user).build(UpdateUser)(user.id, user.id, data)

    async def test_user_cannot_update_others(self) -> None:
        alice, bob = make_user(), make_user()
        with pytest.raises(ForbiddenError):
            await Context(alice, bob).build(UpdateUser)(alice.id, bob.id, UserUpdateBody(full_name="Xx"))

    async def test_admin_deactivation_revokes_sessions(self) -> None:
        admin, user = make_user(UserRole.ADMIN), make_user()
        ctx = Context(admin, user)

        await ctx.build(UpdateUser)(admin.id, user.id, UserUpdateBody(full_name="Xx", is_active=False))

        assert user.is_active is False
        assert ctx.tokens.revoked == [user.id]


class TestDeactivateUser:
    async def test_deactivates_and_revokes_sessions(self) -> None:
        admin, user = make_user(UserRole.ADMIN), make_user()
        ctx = Context(admin, user)

        await ctx.build(DeactivateUser)(admin.id, user.id)

        assert user.is_active is False
        assert ctx.tokens.revoked == [user.id]
        assert ctx.uow.committed

    async def test_requires_admin(self) -> None:
        actor, user = make_user(), make_user()
        with pytest.raises(ForbiddenError):
            await Context(actor, user).build(DeactivateUser)(actor.id, user.id)

    async def test_unknown_user(self) -> None:
        admin = make_user(UserRole.ADMIN)
        with pytest.raises(UserNotFoundError):
            await Context(admin).build(DeactivateUser)(admin.id, uuid4())
