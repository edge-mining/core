"""Collection of adapters configuration for the energy domain of the Edge Mining application."""

from dataclasses import asdict, dataclass, field

from edge_mining.domain.common import Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.shared.interfaces.config import EnergyMonitorConfig


@dataclass(frozen=True)
class EnergyMonitorDummySolarConfig(EnergyMonitorConfig):
    """Energy monitor configuration"""

    max_consumption_power: Watts = field(default=Watts(3200.0))  # Default max consumption power

    def is_valid(self, adapter_type: EnergyMonitorAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Dummy Solar, it is always valid.
        """
        return adapter_type == EnergyMonitorAdapter.DUMMY_SOLAR

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)


@dataclass(frozen=True)
class EnergyMonitorHomeAssistantConfig(EnergyMonitorConfig):
    """
    Energy monitor configuration. It encapsulate the configuration parameters
    to retrieve energy data from Home Assistant.
    """

    entity_production: str
    entity_consumption: str
    entity_grid: str = field(default="")
    entity_battery_soc: str = field(default="")
    entity_battery_power: str = field(default="")
    entity_battery_remaining_capacity: str = field(default="")
    unit_production: str = field(default="W")
    unit_consumption: str = field(default="W")
    unit_grid: str = field(default="W")
    unit_battery_power: str = field(default="W")
    unit_battery_remaining_capacity: str = field(default="Wh")
    grid_positive_export: bool = field(default=False)
    battery_positive_charge: bool = field(default=True)

    def is_valid(self, adapter_type: EnergyMonitorAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Home Assistant, it is always valid.
        """
        return adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_API

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
