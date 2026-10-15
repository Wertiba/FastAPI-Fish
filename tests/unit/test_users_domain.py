"""Доменная логика и интеракторы тестируются без БД и HTTP — на фейках портов."""

from uuid import UUID, uuid4

import pytest

from app.modules.users.application.commands import DeactivateUser
from app.modules.users.application.ports import UserFilter
from app.modules.users.domain.entities import User
from app.modules.users.domain.errors import UserNotFoundError
from app.modules.users.public import UserDeactivated
from app.shared.application.events import Event
from app.shared.application.pagination import Pagination
from app.shared.domain.errors import AccessDeniedError
from app.shared.domain.identity import Identity, UserRole


def make_user(role: UserRole = UserRole.USER) -> User:
    return User.create(email=f"{uuid4().hex}@example.com", password_hash="h", full_name="U", role=role)


class TestUserEntity:
    def test_create_sets_self_as_creator_by_default(self) -> None:
        user = make_user()
        assert user.created_by == user.id
        assert user.created_at == user.updated_at
        assert user.created_at.tzinfo is not None

    def test_user_can_change_own_name(self) -> None:
        user = make_user()
        deactivated = user.update(
            full_name="New", role=None, is_active=None, actor=Identity(user.id, UserRole.USER)
        )
        assert user.full_name == "New"
        assert deactivated is False

    @pytest.mark.parametrize(("role", "is_active"), [(UserRole.ADMIN, None), (None, False)])
    def test_user_cannot_change_role_or_status(self, role: UserRole | None, is_active: bool | None) -> None:
        user = make_user()
        with pytest.raises(AccessDeniedError):
            user.update(full_name="X", role=role, is_active=is_active, actor=Identity(user.id, UserRole.USER))

    def test_setting_same_values_is_allowed_for_user(self) -> None:
        user = make_user()
        user.update(full_name="X", role=UserRole.USER, is_active=True, actor=Identity(user.id, UserRole.USER))

    def test_admin_deactivation_is_reported(self) -> None:
        user = make_user()
        deactivated = user.update(
            full_name="X", role=None, is_active=False, actor=Identity(uuid4(), UserRole.ADMIN)
        )
        assert deactivated is True
        assert user.is_active is False


# --- фейки портов -------------------------------------------------------------


class FakeIdentityProvider:
    def __init__(self, identity: Identity) -> None:
        self.identity = identity

    async def get_identity(self) -> Identity:
        return self.identity


class InMemoryUsers:
    def __init__(self, *users: User) -> None:
        self.items = {u.id: u for u in users}

    async def add(self, user: User) -> None:
        self.items[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.items.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.items.values() if u.email == email), None)

    async def find(self, filters: UserFilter, pagination: Pagination) -> list[User]:
        return list(self.items.values())

    async def count(self, filters: UserFilter) -> int:
        return len(self.items)


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def publish(self, event: Event) -> None:
        self.events.append(event)


class FakeTransaction:
    committed = False

    async def commit(self) -> None:
        self.committed = True

    async def flush(self) -> None:
        pass


class TestDeactivateUser:
    async def test_deactivates_and_publishes_event(self) -> None:
        user = make_user()
        events, tx = RecordingPublisher(), FakeTransaction()
        interactor = DeactivateUser(
            FakeIdentityProvider(Identity(uuid4(), UserRole.ADMIN)), InMemoryUsers(user), events, tx
        )

        await interactor(user.id)

        assert user.is_active is False
        assert events.events == [UserDeactivated(user_id=user.id)]
        assert tx.committed

    async def test_requires_admin(self) -> None:
        user = make_user()
        interactor = DeactivateUser(
            FakeIdentityProvider(Identity(uuid4(), UserRole.USER)),
            InMemoryUsers(user),
            RecordingPublisher(),
            FakeTransaction(),
        )
        with pytest.raises(AccessDeniedError):
            await interactor(user.id)

    async def test_unknown_user(self) -> None:
        interactor = DeactivateUser(
            FakeIdentityProvider(Identity(uuid4(), UserRole.ADMIN)),
            InMemoryUsers(),
            RecordingPublisher(),
            FakeTransaction(),
        )
        with pytest.raises(UserNotFoundError):
            await interactor(uuid4())
