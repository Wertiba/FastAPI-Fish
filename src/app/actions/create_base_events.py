from sqlalchemy import select

from app.core.logger import Logger
from app.infrastructure.models import EventCatalog


async def create_base_events(session):
    logger = Logger().get_logger()

    default_events = [
        {
            "code": "EXPOSURE",
            "name": "Экспозиция",
            "description": "Факт показа варианта пользователю. Базовое системное событие для атрибуции.",
            "requiredParams": None,
            "requiresExposure": False,
            "isSystem": True,
        },
        {
            "code": "CONVERSION",
            "name": "Конверсия",
            "description": "Целевое действие пользователя. Требует факта показа для атрибуции.",
            "requiredParams": None,
            "requiresExposure": True,
            "isSystem": True,
        },
        {
            "code": "ERROR",
            "name": "Ошибка",
            "description": "Факт ошибки в ходе сессии пользователя.",
            "requiredParams": {"message": "string"},
            "requiresExposure": False,
            "isSystem": True,
        },
        {
            "code": "LATENCY",
            "name": "Задержка",
            "description": "Время ответа в миллисекундах. Поле data.value_ms обязательно.",
            "requiredParams": {"value_ms": "number"},
            "requiresExposure": False,
            "isSystem": True,
        },
        {
            "code": "CLICK",
            "name": "Клик",
            "description": "Клик по любому элементу интерфейса.",
            "requiredParams": None,
            "requiresExposure": True,
            "isSystem": True,
        },
        {
            "code": "PURCHASE",
            "name": "Покупка",
            "description": "Факт покупки. Поле data.amount обязательно для метрик выручки.",
            "requiredParams": {"amount": "number"},
            "requiresExposure": True,
            "isSystem": True,
        },
    ]

    for event_data in default_events:
        stmt = select(EventCatalog).where(EventCatalog.code == event_data["code"])   # noqa
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            event = EventCatalog(**event_data)
            session.add(event)

    await session.commit()
    logger.info("All base events created successfully!")
