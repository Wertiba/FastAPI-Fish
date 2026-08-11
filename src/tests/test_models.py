# src/tests/test_models.py
from sqlalchemy import create_engine, inspect

from app.core.enums import UserRole
from app.infrastructure.models import Base, RefreshToken, User


def test_tables_have_expected_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {"users", "refresh_tokens"}

    user_columns = {c["name"] for c in inspector.get_columns("users")}
    assert user_columns == {
        "id", "email", "password", "full_name", "role",
        "is_active", "created_by", "created_at", "updated_at",
    }

    token_columns = {c["name"] for c in inspector.get_columns("refresh_tokens")}
    assert token_columns == {"id", "user_id", "hashed_token", "expires_at", "created_at"}


def test_user_role_enum_values():
    assert {member.value for member in UserRole} == {"USER", "ADMIN"}


def test_schemas_user_role_is_the_canonical_enum():
    from app.core.schemas.user import UserRole as SchemaUserRole

    assert SchemaUserRole is UserRole
