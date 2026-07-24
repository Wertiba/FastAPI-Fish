from app.core.exceptions.base import EntityError


class MetricNotFoundError(EntityError):
    pass


class MetricAlreadyExistsError(EntityError):
    pass
