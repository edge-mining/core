"""Collection of Ports for the Energy System Monitoring domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import List, Optional

from edge_mining.domain.common import EntityId
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.energy.entities import EnergyMonitor, EnergySource
from edge_mining.domain.energy.value_objects import EnergyStateSnapshot


class EnergyMonitorPort(ABC):
    """Port for the Energy Monitor."""

    def __init__(self, energy_monitor_type: EnergyMonitorAdapter):
        """Initialize the Energy Monitor."""
        self.energy_monitor_type = energy_monitor_type

    @abstractmethod
    def get_current_energy_state(self) -> Optional[EnergyStateSnapshot]:
        """Fetches the latest energy readings from the plant."""
        raise NotImplementedError


class EnergySourceRepository(ABC):
    """Port for the Energy Source Repository."""

    @abstractmethod
    def add(self, energy_source: EnergySource) -> None:
        """Adds a new energy source to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, energy_source_id: EntityId) -> Optional[EnergySource]:
        """Retrieves an energy source by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[EnergySource]:
        """Retrieves all energy sources from the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, energy_source: EnergySource) -> None:
        """Updates an energy source in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, energy_source_id: EntityId) -> None:
        """Removes an energy source from the repository."""
        raise NotImplementedError


class EnergyMonitorRepository(ABC):
    """Port for the Energy Monitor Repository."""

    @abstractmethod
    def add(self, energy_monitor: EnergyMonitor) -> None:
        """Adds a new energy monitor to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, energy_monitor_id: EntityId) -> Optional[EnergyMonitor]:
        """Retrieves an energy monitor by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[EnergyMonitor]:
        """Retrieves all energy monitors from the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, energy_monitor: EnergyMonitor) -> None:
        """Updates an energy monitor in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, energy_monitor_id: EntityId) -> None:
        """Removes an energy monitor from the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external_service_id(self, external_service_id: EntityId) -> List[EnergyMonitor]:
        """Retrieves a list of energy monitors by its associated external service ID."""
        raise NotImplementedError
