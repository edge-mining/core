"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class HomeLoadError(DomainError):
    """Base class for home load-related errors."""

    pass


class HomeForecastError(HomeLoadError):
    """Base class for home forecast-specific errors."""

    pass


class HomeForecastProviderError(HomeForecastError):
    """Errors related to home forecast provider."""

    pass


class HomeForecastProviderNotFoundError(HomeForecastProviderError):
    """Home Forecast Provider not found."""

    pass


class HomeForecastProviderAlreadyExistsError(HomeForecastProviderError):
    """Home Forecast Provider already exists."""

    pass


class HomeForecastProviderConfigurationError(HomeForecastProviderError):
    """Error with the configuration."""

    pass
