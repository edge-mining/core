"""Collection of Ports for the Energy Forecast domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import List, Optional

from edge_mining.domain.common import EntityId
from edge_mining.domain.forecast.aggregate_root import Forecast
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.forecast.entities import ForecastProvider


class ForecastProviderPort(ABC):
    """Port for the Forecast Provider."""

    def __init__(self, forecast_provider_type: ForecastProviderAdapter):
        """Initialize the Forecast Provider."""
        self.forecast_provider_type = forecast_provider_type

    @abstractmethod
    def get_forecast(self) -> Optional[Forecast]:
        """Fetches the energy production forecast."""
        raise NotImplementedError


class ForecastProviderRepository(ABC):
    """Port for the Energy Monitor Repository."""

    @abstractmethod
    def add(self, forecast_provider: ForecastProvider) -> None:
        """Adds a new forecast provider to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, forecast_provider_id: EntityId) -> Optional[ForecastProvider]:
        """Retrieves a forecast provider by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[ForecastProvider]:
        """Retrieves all forecast providers from the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, forecast_provider: ForecastProvider) -> None:
        """Updates a forecast provider in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, forecast_provider_id: EntityId) -> None:
        """Removes a forecast provider from the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external_service_id(self, external_service_id: EntityId) -> List[ForecastProvider]:
        """Retrieves a list of forecast providers by its associated external service ID."""
        raise NotImplementedError
