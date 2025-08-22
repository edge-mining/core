"""Collection of Ports for the Energy Optimization Unit domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import List, Optional

from edge_mining.domain.common import EntityId
from edge_mining.domain.optimization_unit.aggregate_roots import EnergyOptimizationUnit


class EnergyOptimizationUnitRepository(ABC):
    """Port for the Energy Optimization Unit Repository."""

    @abstractmethod
    def add(self, optimization_unit: EnergyOptimizationUnit) -> None:
        """Add an energy optimization unit to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, optimization_unit_id: EntityId) -> Optional[EnergyOptimizationUnit]:
        """Get an energy optimization unit by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all_enabled(self) -> List[EnergyOptimizationUnit]:
        """Get all enabled energy optimization units."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[EnergyOptimizationUnit]:
        """Get all energy optimization units."""
        raise NotImplementedError

    @abstractmethod
    def update(self, optimization_unit: EnergyOptimizationUnit) -> None:
        """Update an energy optimization unit in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, optimization_unit_id: EntityId) -> None:
        """Remove an energy optimization unit from the repository."""
        raise NotImplementedError
