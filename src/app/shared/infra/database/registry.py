"""The one SQLAlchemy registry every module maps its tables onto.

Each module keeps its tables and mappers in ``modules/<name>/infra/tables.py``; importing the
module registers them here. Alembic autogenerate and the tests read ``metadata`` after
``app.bootstrap`` has imported every module.
"""

from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import FromClause, MetaData
from sqlalchemy.orm import registry

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

mapper_registry = registry(metadata=MetaData(naming_convention=NAMING_CONVENTION))
metadata = mapper_registry.metadata


def str_enum(enum_cls: type[Enum], name: str, length: int = 20) -> SAEnum:
    """Enum stored as plain VARCHAR with the member values."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
    )


def map_once(entity: type, table: FromClause) -> None:
    """Imperative mapping that is safe to call again (module import, ASGI startup, Alembic)."""
    if any(mapper.class_ is entity for mapper in mapper_registry.mappers):
        return
    mapper_registry.map_imperatively(entity, table)
