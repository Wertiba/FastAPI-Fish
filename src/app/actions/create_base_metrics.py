from sqlalchemy import select

from app.core.logger import Logger
from app.core.schemas.metric import AggregationUnit, MetricType
from app.infrastructure.models import MetricCatalog


async def create_base_metrics(session):
    logger = Logger().get_logger()

    default_metrics = [
        {
            "code": "IMPRESSIONS",
            "name": "Число показов",
            "type": MetricType.COUNT,
            "aggregationUnit": AggregationUnit.EVENT,
            "isSystem": True,
            "description": "Общее количество показов",
            "calculationConfig": None,
        },
        {
            "code": "CONVERSIONS",
            "name": "Число конверсий",
            "type": MetricType.COUNT,
            "aggregationUnit": AggregationUnit.EVENT,
            "isSystem": True,
            "description": "Общее количество конверсий",
            "calculationConfig": None,
        },
        {
            "code": "CONVERSION_RATE",
            "name": "Доля конверсий",
            "type": MetricType.RATIO,
            "aggregationUnit": AggregationUnit.USER,
            "isSystem": True,
            "description": "Доля пользователей, совершивших конверсию",
            "calculationConfig": {
                "numerator": "CONVERSIONS",
                "denominator": "IMPRESSIONS",
            },
        },

        {
            "code": "ERRORS",
            "name": "Число ошибок",
            "type": MetricType.COUNT,
            "aggregationUnit": AggregationUnit.EVENT,
            "isSystem": True,
            "description": "Общее количество ошибок",
            "calculationConfig": None,
        },
        {
            "code": "ERROR_RATE",
            "name": "Доля ошибок",
            "type": MetricType.RATIO,
            "aggregationUnit": AggregationUnit.USER,
            "isSystem": True,
            "description": "Доля запросов, завершившихся ошибкой",
            "calculationConfig": {
                "numerator": "ERRORS",
                "denominator": "IMPRESSIONS",
            },
        },

        {
            "code": "AVG_LATENCY",
            "name": "Средняя задержка",
            "type": MetricType.AVG,
            "aggregationUnit": AggregationUnit.EVENT,
            "isSystem": True,
            "description": "Среднее время ответа в миллисекундах",
            "calculationConfig": {
                "unit": "ms",
            },
        },
        {
            "code": "P95_LATENCY",
            "name": "95-й перцентиль задержки",
            "type": MetricType.AVG,
            "aggregationUnit": AggregationUnit.EVENT,
            "isSystem": True,
            "description": "95-й перцентиль времени ответа в миллисекундах",
            "calculationConfig": {
                "percentile": 95,
                "unit": "ms",
            },
        },
    ]

    for metric_data in default_metrics:
        stmt = select(MetricCatalog).where(MetricCatalog.code == metric_data["code"])   # noqa
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            metric = MetricCatalog(**metric_data)
            session.add(metric)

    await session.commit()
    logger.info("All base metrics created successfully!")
