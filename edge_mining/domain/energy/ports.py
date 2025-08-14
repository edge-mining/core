"""Collection of Ports for the Energy System Monitoring domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import Optional

from edge_mining.domain.energy.value_objects import EnergyStateSnapshot
from edge_mining.domain.energy.common import EnergyMonitorAdapter

class EnergyMonitorPort(ABC):
    """Port for the Energy Monitor."""
    @abstractmethod
    def __init__(self, energy_monitor_type: EnergyMonitorAdapter):
        """Initialize the Energy Monitor."""
        self.energy_monitor_type = energy_monitor_type

    @abstractmethod
    def get_current_energy_state(self) -> Optional[EnergyStateSnapshot]:
        """Fetches the latest energy readings from the plant."""
        raise NotImplementedError