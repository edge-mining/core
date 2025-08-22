"""Collection of Exceptions for the Edge Mining application domain."""


class DomainError(Exception):
    """Base class for domain-specific errors."""

    pass


class ConfigurationError(DomainError):
    """Errors related to system configuration."""

    pass
