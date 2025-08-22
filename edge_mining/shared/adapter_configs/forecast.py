"""
Collection of adapters configuration for the energy forecast domain
of the Edge Mining application.
"""

from dataclasses import asdict, dataclass, field

from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.shared.interfaces.config import ForecastProviderConfig


@dataclass(frozen=False)
class ForecastProviderDummySolarConfig(ForecastProviderConfig):
    """
    Forecast provider configuration. It encapsulate the configuration parameters
    to retrieve forecast data from a dummy solar forecast provider.
    """

    latitude: float = field(default=41.90)
    longitude: float = field(default=12.49)
    capacity_kwp: float = field(default=0.0)
    efficiency_percent: float = field(default=80.0)
    production_start_hour: int = field(default=6)
    production_end_hour: int = field(default=20)

    def is_valid(self, adapter_type: ForecastProviderAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Dummy Solar, it is always valid.
        """
        return adapter_type == ForecastProviderAdapter.DUMMY_SOLAR

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)


@dataclass(frozen=True)
class ForecastProviderHomeAssistantConfig(ForecastProviderConfig):
    """
    Forecast provider configuration. It encapsulate the configuration parameters
    to retrieve forecast data from Home Assistant.
    """

    entity_forecast_power_actual_h: str = field(default="")
    entity_forecast_power_next_1h: str = field(default="")
    entity_forecast_power_next_12h: str = field(default="")
    entity_forecast_power_next_24h: str = field(default="")
    entity_forecast_energy_actual_h: str = field(default="")
    entity_forecast_energy_next_1h: str = field(default="")
    entity_forecast_energy_today: str = field(default="")
    entity_forecast_energy_tomorrow: str = field(default="")
    entity_forecast_energy_remaining_today: str = field(default="")
    unit_forecast_power_actual_h: str = field(default="W")
    unit_forecast_power_next_1h: str = field(default="W")
    unit_forecast_power_next_12h: str = field(default="W")
    unit_forecast_power_next_24h: str = field(default="W")
    unit_forecast_energy_actual_h: str = field(default="kWh")
    unit_forecast_energy_next_1h: str = field(default="kWh")
    unit_forecast_energy_today: str = field(default="kWh")
    unit_forecast_energy_tomorrow: str = field(default="kWh")
    unit_forecast_energy_remaining_today: str = field(default="kWh")

    def is_valid(self, adapter_type: ForecastProviderAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Home Assistant, it is always valid.
        """
        return adapter_type == ForecastProviderAdapter.HOME_ASSISTANT_API

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
