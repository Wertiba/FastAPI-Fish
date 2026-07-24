from app.core.exceptions.base import EntityError


class ExperimentNotFoundError(EntityError):
    pass


class ExperimentAlreadyExistsError(EntityError):
    pass


class VersionOfExperimentAlreadyExistsError(EntityError):
    pass


class ExperimentInvalidStatusError(EntityError):
    pass


class ExperimentReworkError(EntityError):
    pass


class ExperimentAlreadyRunningError(EntityError):
    pass
