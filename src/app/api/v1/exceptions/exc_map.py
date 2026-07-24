from app.api.v1.exceptions.api_exs import (
    Conflict,
    Forbidden,
    Inactive,
    NotFound,
    Unauthorized,
    ValidationFailed,
)
from app.core.exceptions.base import UnprocessableEntityError
from app.core.exceptions.event_exs import EventAlreadyExistsError, EventNotFoundError
from app.core.exceptions.experiment_exs import (
    ExperimentAlreadyExistsError,
    ExperimentAlreadyRunningError,
    ExperimentInvalidStatusError,
    ExperimentNotFoundError,
    ExperimentReworkError,
    VersionOfExperimentAlreadyExistsError,
)
from app.core.exceptions.flag_exs import FlagAlreadyExistsError, FlagNotFoundError
from app.core.exceptions.metric_exs import MetricAlreadyExistsError, MetricNotFoundError
from app.core.exceptions.review_exs import ReviewAlreadyExistsError, ReviewNotFoundError
from app.core.exceptions.user_exs import (
    DeficiencyApproversError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotActiveError,
    UserNotFoundError,
)

DOMAIN_TO_API: dict[type, callable] = {
    UserNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="User not found",
    ),
    FlagNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="Flag not found",
    ),
    MetricNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="Metric not found",
    ),
    EventNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="Event not found",
    ),
    ExperimentNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="Experiment not found",
    ),
    ReviewNotFoundError: lambda path, exc=None: NotFound(
        path=path,
        message="Review not found",
    ),
    ForbiddenError: lambda path, exc=None: Forbidden(
        path=path,
    ),
    InvalidCredentialsError: lambda path, exc=None: Unauthorized(
        path=path,
    ),
    InvalidPasswordError: lambda path, exc=None: Unauthorized(
        path=path,
    ),
    ExperimentInvalidStatusError: lambda path, exc=None: Conflict(
        path=path,
        message="Invalid experiment status",
    ),
    ExperimentReworkError: lambda path, exc=None: Conflict(
        path=path,
        message="Experiment need to be changed after reviews",
    ),
    ExperimentAlreadyRunningError: lambda path, exc=None: Conflict(
        path=path,
        message="Another experiment for this flag already in status running or paused",
    ),
    VersionOfExperimentAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="Invalid experiment version",
    ),
    UserAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="User already exists",
    ),
    FlagAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="Flag already exists",
    ),
    MetricAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="Metric already exists",
    ),
    EventAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="Event already exists",
    ),
    ExperimentAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="Experiment already exists",
    ),
    ReviewAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="Review already exists",
    ),
    UnprocessableEntityError: lambda path, exc=None: ValidationFailed(
        path=path,
    ),
    DeficiencyApproversError: lambda path, exc=None: ValidationFailed(
        path=path,
        message="Invalid number of approvers"
    ),
    UserNotActiveError: lambda path, exc=None: Inactive(
        path=path,
    ),
}
