"""Collection of Ports for the Energy Forecast domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import Optional

from edge_mining.domain.forecast.value_objects import ForecastData

class ForecastProviderPort(ABC):
    """Port for the Forecast Provider."""
    @abstractmethod
    def get_solar_forecast(self) -> Optional[ForecastData]:
        """Fetches the solar energy production forecast."""
        raise NotImplementedError