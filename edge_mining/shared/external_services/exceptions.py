"""Collection of Exceptions."""


class ExternalServiceError(Exception):
    """Base class for external service specific errors."""

    pass


class ExternalServiceNotFoundError(ExternalServiceError):
    """External Service not found."""

    pass


class ExternalServiceAlreadyExistsError(ExternalServiceError):
    """ExternalService already exists."""

    pass


class ExternalServiceConfigurationError(ExternalServiceError):
    """Errors related to external service configuration."""

    pass
