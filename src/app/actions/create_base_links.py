from sqlmodel import select

from app.core.logger import Logger
from app.infrastructure.models.event import EventMetricLink


async def create_base_links(session):
    logger = Logger().get_logger()

    default_links = [
        # EXPOSURE → IMPRESSIONS
        {
            "eventCatalog_code": "EXPOSURE",
            "metricCatalog_code": "IMPRESSIONS",
            "role": None,
            "value_field": None,
            "description": "Показ считается как impression",
        },

        # CONVERSION → CONVERSIONS
        {
            "eventCatalog_code": "CONVERSION",
            "metricCatalog_code": "CONVERSIONS",
            "role": None,
            "value_field": None,
            "description": "Конверсия считается как conversion",
        },

        # CONVERSION_RATE = CONVERSION / EXPOSURE  # noqa: ERA001
        {
            "eventCatalog_code": "CONVERSION",
            "metricCatalog_code": "CONVERSION_RATE",
            "role": "numerator",
            "value_field": None,
            "description": "Числитель доли конверсий",
        },
        {
            "eventCatalog_code": "EXPOSURE",
            "metricCatalog_code": "CONVERSION_RATE",
            "role": "denominator",
            "value_field": None,
            "description": "Знаменатель доли конверсий",
        },

        # ERROR → ERRORS
        {
            "eventCatalog_code": "ERROR",
            "metricCatalog_code": "ERRORS",
            "role": None,
            "value_field": None,
            "description": "Ошибка считается как error",
        },

        # ERROR_RATE = ERROR / EXPOSURE  # noqa: ERA001
        {
            "eventCatalog_code": "ERROR",
            "metricCatalog_code": "ERROR_RATE",
            "role": "numerator",
            "value_field": None,
            "description": "Числитель доли ошибок",
        },
        {
            "eventCatalog_code": "EXPOSURE",
            "metricCatalog_code": "ERROR_RATE",
            "role": "denominator",
            "value_field": None,
            "description": "Знаменатель доли ошибок",
        },

        # LATENCY → AVG_LATENCY
        {
            "eventCatalog_code": "LATENCY",
            "metricCatalog_code": "AVG_LATENCY",
            "role": None,
            "value_field": "value_ms",
            "description": "Задержка в мс для расчёта среднего",
        },

        # LATENCY → P95_LATENCY
        {
            "eventCatalog_code": "LATENCY",
            "metricCatalog_code": "P95_LATENCY",
            "role": None,
            "value_field": "value_ms",
            "description": "Задержка в мс для расчёта перцентиля",
        },
    ]

    for link_data in default_links:
        stmt = select(EventMetricLink).where(
            EventMetricLink.eventCatalog_code == link_data["eventCatalog_code"],    # noqa
            EventMetricLink.metricCatalog_code == link_data["metricCatalog_code"],  # noqa
            EventMetricLink.role == link_data["role"],  # noqa
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            link = EventMetricLink(**link_data)
            session.add(link)

    await session.commit()
    logger.info("All base event-metric links created successfully!")
