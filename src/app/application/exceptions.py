class ApplicationError(Exception):
    """Base for failures raised by application ports and adapters."""


class DuplicateError(ApplicationError):
    """Violation of a uniqueness constraint."""
