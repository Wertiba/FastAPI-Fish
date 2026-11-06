class ApplicationError(Exception):
    """Base for failures raised by application ports and adapters."""


class DuplicateError(ApplicationError):
    """Violation of a uniqueness constraint."""


class ServiceUnavailableError(ApplicationError):
    """An external system (LLM, storage, broker) is disabled or down; the API answers 503."""
