"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class ForecastError(DomainError):
    """Base class for forecast-specific errors."""

    pass


class ForecastProviderError(ForecastError):
    """Errors related to forecast provider."""

    pass


class ForecastProviderNotFoundError(ForecastProviderError):
    """Forecast Provider not found."""

    pass


class ForecastProviderAlreadyExistsError(ForecastProviderError):
    """Forecast Provider already exists."""

    pass


class ForecastProviderConfigurationError(ForecastProviderError):
    """Error with the configuration."""

    pass
