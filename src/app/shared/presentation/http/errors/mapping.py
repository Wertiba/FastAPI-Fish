"""Domain error -> API error. Each module contributes its own ``ErrorMap``; the composition root merges them.

The first ``isinstance`` match wins, so module maps (subclasses) go before ``SHARED_ERRORS`` (bases).
"""

from collections.abc import Callable, Mapping
from typing import Any

from app.shared.domain.errors import ForbiddenError, InvalidCredentialsError, UnprocessableEntityError
from app.shared.presentation.http.errors.api_exs import Forbidden, Unauthorized, ValidationFailed
from app.shared.presentation.http.errors.base import APIException

type ErrorFactory = Callable[[str, Any], APIException]
type ErrorMap = Mapping[type[Exception], ErrorFactory]

SHARED_ERRORS: ErrorMap = {
    ForbiddenError: lambda path, exc: Forbidden(path=path),
    InvalidCredentialsError: lambda path, exc: Unauthorized(path=path),
    UnprocessableEntityError: lambda path, exc: ValidationFailed(path=path),
}
