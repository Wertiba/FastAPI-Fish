"""
conftest.py — общие фикстуры для тестов LOTTY A/B Platform.

Стратегия:
- SQLite (aiosqlite) in-memory вместо PostgreSQL — изолированная тестовая БД
- Каждый тест-модуль получает чистую БД через функциональную фикстуру `session`
- FastAPI приложение подменяет зависимость get_session на тестовую
- Все фикстуры async, pytest-asyncio в режиме auto

Запуск:
    pip install pytest pytest-asyncio httpx aiosqlite
    pytest tests/ -v --tb=short
    pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
"""

# ── Patch settings BEFORE app import ─────────────────────────────────────────
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.hash import argon2
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.ru")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass")
os.environ.setdefault("ADMIN_FULLNAME", "Test Admin")

from app.core.schemas.metric import AggregationUnit, MetricType
from app.core.schemas.role import RoleCode
from app.infrastructure.database.db_helper import db_helper  # noqa: E402
from app.infrastructure.models import (  # noqa: E402
    Role,
    User,
    UserRole,
)
from app.infrastructure.models.event import EventCatalog, EventMetricLink
from app.infrastructure.models.flag import Flag
from app.infrastructure.models.metric import MetricCatalog
from app.main import app  # noqa: E402

# ── Test engine: SQLite in-memory ────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def override_session_getter() -> AsyncIterator[AsyncSession]:
    async with TestSessionFactory() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Создать все таблицы один раз на сессию."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with TestSessionFactory() as session:
        KEEP_TABLES = {"roles"}
        for table in reversed(SQLModel.metadata.sorted_tables):
            if table.name not in KEEP_TABLES:
                await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with TestSessionFactory() as s:
        yield s


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP-клиент, подключённый к тестовому FastAPI приложению."""
    app.dependency_overrides[db_helper.session_getter] = override_session_getter
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── Вспомогательные фикстуры: базовые данные ─────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def roles():
    async with TestSessionFactory() as session:
        roles_data = [
            Role(code=RoleCode.ADMN, value="Admin", description="Full access"),
            Role(code=RoleCode.EXPR, value="Experimenter", description="Can create experiments"),
            Role(code=RoleCode.APPR, value="Approver", description="Can approve"),
            Role(code=RoleCode.VIEW, value="Viewer", description="Read only"),
        ]
        for r in roles_data:
            session.add(r)
        await session.commit()
        for r in roles_data:
            await session.refresh(r)
        return {r.code: r for r in roles_data}


def _hash(password: str) -> str:
    return argon2.hash(password)


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession, roles):
    """Создать пользователя с ролью ADMN."""
    user = User(
        email="admin@test.ru",
        password=_hash("adminpass"),
        fullName="Test Admin",
        exp_index=100,
        required=0,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.ADMN].id))
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def experimenter_user(session: AsyncSession, roles):
    """Создать пользователя с ролью EXPR (required=0 — может создавать без approver)."""
    user = User(
        email="experimenter@test.ru",
        password=_hash("exprpass"),
        fullName="Test Experimenter",
        exp_index=100,
        required=0,  # 0 = approver не нужен; для теста ревью используй experimenter_with_required
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.EXPR].id))
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def experimenter_with_required(session: AsyncSession, roles):
    """Experimenter с required=1 — для тестов, где нужен обязательный approver."""
    user = User(
        email="experimenter_req@test.ru",
        password=_hash("exprreqpass"),
        fullName="Test Experimenter Required",
        exp_index=100,
        required=1,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.EXPR].id))
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def approver_user(session: AsyncSession, roles):
    """Создать пользователя с ролью APPR."""
    user = User(
        email="approver@test.ru",
        password=_hash("apprpass"),
        fullName="Test Approver",
        exp_index=100,
        required=0,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.APPR].id))
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(session: AsyncSession, roles):
    """Создать пользователя с ролью VIEW."""
    user = User(
        email="viewer@test.ru",
        password=_hash("viewpass"),
        fullName="Test Viewer",
        exp_index=100,
        required=0,
    )
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.VIEW].id))
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_users(session: AsyncSession, roles):
    """5 тестовых пользователей (как в демо-скриптах)."""
    users = []
    for i in range(1, 6):
        u = User(
            email=f"user{i}@test.ru",
            password=_hash(f"user{i}pass"),
            fullName=f"Test User {i}",
            exp_index=100,
            required=0,
        )
        session.add(u)
        await session.flush()
        session.add(UserRole(user_id=u.id, role_id=roles[RoleCode.VIEW].id))
        users.append(u)
    await session.commit()
    for u in users:
        await session.refresh(u)
    return users


@pytest_asyncio.fixture
async def flag_button_color(session: AsyncSession, admin_user):
    """Флаг button_color как в 02_flags.sh."""
    flag = Flag(
        code="button_color",
        default="green",
        type="STRING",
        createdBy=admin_user.id,
    )
    session.add(flag)
    await session.commit()
    await session.refresh(flag)
    return flag


@pytest_asyncio.fixture
async def flag_show_banner(session: AsyncSession, admin_user):
    """Флаг show_banner."""
    flag = Flag(
        code="show_banner",
        default="false",
        type="BOOL",
        createdBy=admin_user.id,
    )
    session.add(flag)
    await session.commit()
    await session.refresh(flag)
    return flag


@pytest_asyncio.fixture
async def base_events_catalog(session: AsyncSession):
    """Базовые события каталога (как create_base_events.py)."""
    events = [
        EventCatalog(code="EXPOSURE",   name="Exposure",   requiresExposure=False, isSystem=True),
        EventCatalog(code="CONVERSION", name="Conversion", requiresExposure=True,  isSystem=True),
        EventCatalog(code="ERROR",      name="Error",      requiresExposure=False, isSystem=True),
        EventCatalog(code="LATENCY",    name="Latency",    requiresExposure=False, isSystem=True),
        EventCatalog(code="CLICK",      name="Click",      requiresExposure=False, isSystem=True),
        EventCatalog(code="PURCHASE",   name="Purchase",   requiresExposure=True,  isSystem=True),
    ]
    for e in events:
        session.add(e)
    await session.commit()
    return {e.code: e for e in events}


@pytest_asyncio.fixture
async def base_metrics_catalog(session: AsyncSession):
    """Базовые метрики каталога."""
    metrics = [
        MetricCatalog(code="IMPRESSIONS",      name="Impressions",      type=MetricType.COUNT, aggregationUnit=AggregationUnit.EVENT, isSystem=True),
        MetricCatalog(code="CONVERSIONS",      name="Conversions",      type=MetricType.COUNT, aggregationUnit=AggregationUnit.EVENT, isSystem=True),
        MetricCatalog(code="CONVERSION_RATE",  name="Conversion Rate",  type=MetricType.RATIO, aggregationUnit=AggregationUnit.EVENT, isSystem=True),
        MetricCatalog(code="ERRORS",           name="Errors",           type=MetricType.COUNT, aggregationUnit=AggregationUnit.EVENT, isSystem=True),
        MetricCatalog(code="ERROR_RATE",       name="Error Rate",       type=MetricType.RATIO, aggregationUnit=AggregationUnit.EVENT, isSystem=True),
        MetricCatalog(code="AVG_LATENCY",      name="Avg Latency",      type=MetricType.AVG,   aggregationUnit=AggregationUnit.EVENT, isSystem=True),
    ]
    for m in metrics:
        session.add(m)
    await session.commit()
    return {m.code: m for m in metrics}


@pytest_asyncio.fixture
async def event_metric_links(session: AsyncSession, base_events_catalog, base_metrics_catalog):
    """EventMetricLink: связи событий с метриками (как в 01_setup.sh)."""
    links = [
        EventMetricLink(metricCatalog_code="IMPRESSIONS",     eventCatalog_code="EXPOSURE",    role="numerator"),
        EventMetricLink(metricCatalog_code="CONVERSIONS",     eventCatalog_code="CONVERSION",  role="numerator"),
        EventMetricLink(metricCatalog_code="CONVERSION_RATE", eventCatalog_code="CONVERSION",  role="numerator"),
        EventMetricLink(metricCatalog_code="CONVERSION_RATE", eventCatalog_code="EXPOSURE",    role="denominator"),
        EventMetricLink(metricCatalog_code="ERRORS",          eventCatalog_code="ERROR",       role="numerator"),
        EventMetricLink(metricCatalog_code="ERROR_RATE",      eventCatalog_code="ERROR",       role="numerator"),
        EventMetricLink(metricCatalog_code="ERROR_RATE",      eventCatalog_code="EXPOSURE",    role="denominator"),
        EventMetricLink(metricCatalog_code="AVG_LATENCY",     eventCatalog_code="LATENCY",     role="numerator", value_field="value_ms"),
    ]
    for lnk in links:
        session.add(lnk)
    await session.commit()
    return links


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    """Вспомогательная: получить JWT токен."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["accessToken"]
    client.cookies.clear()
    return token


async def auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    token = await get_token(client, email, password)
    return {"Authorization": f"Bearer {token}"}
