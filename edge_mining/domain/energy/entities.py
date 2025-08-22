"""Collection of Entities for the Energy System Monitoring domain of the Edge Mining application."""

from dataclasses import dataclass
from typing import Optional

from edge_mining.domain.common import Entity, EntityId, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.energy.value_objects import Battery, Grid
from edge_mining.shared.interfaces.config import EnergyMonitorConfig


@dataclass
class EnergySource(Entity):
    """Entity for an energy source."""

    name: str = ""
    type: EnergySourceType = EnergySourceType.SOLAR
    nominal_power_max: Optional[Watts] = None
    storage: Optional[Battery] = None
    grid: Optional[Grid] = None
    external_source: Optional[Watts] = None  # e.g., external generator

    energy_monitor_id: Optional[EntityId] = None  # Energy monitor to be used
    forecast_provider_id: Optional[EntityId] = None  # Forecast provider to be used

    def connect_to_grid(self, grid: Grid):
        """Connect to the grid."""
        self.grid = grid

    def disconnect_from_grid(self):
        """Disconnect from the grid."""
        self.grid = None

    def connect_to_external_source(self, external_source: Watts):
        """Connect to the external source."""
        self.external_source = external_source

    def disconnect_from_external_source(self):
        """Disconnect from the external source."""
        self.external_source = None

    def connect_to_storage(self, storage: Battery):
        """Connect to the storage."""
        self.storage = storage

    def disconnect_from_storage(self):
        """Disconnect from the storage."""
        self.storage = None

    def use_energy_monitor(self, energy_monitor_id: EntityId):
        """Use the energy monitor."""
        self.energy_monitor_id = energy_monitor_id

    def use_forecast_provider(self, forecast_provider_id: EntityId):
        """Use a forecast provider."""
        self.forecast_provider_id = forecast_provider_id


@dataclass
class EnergyMonitor(Entity):
    """Entity for an energy monitor."""

    name: str = ""
    adapter_type: EnergyMonitorAdapter = EnergyMonitorAdapter.DUMMY_SOLAR
    config: Optional[EnergyMonitorConfig] = None
    external_service_id: Optional[EntityId] = None
