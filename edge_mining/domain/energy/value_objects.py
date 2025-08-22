"""Collection of Value Objects for the Energy System Monitoring domain of the Edge Mining application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from edge_mining.domain.common import (
    Percentage,
    Timestamp,
    ValueObject,
    WattHours,
    Watts,
)


@dataclass(frozen=True)
class Battery(ValueObject):
    """Value Object for a battery."""

    nominal_capacity: WattHours


@dataclass(frozen=True)
class Grid(ValueObject):
    """Value Object for a grid."""

    contracted_power: Watts


@dataclass(frozen=True)
class LoadState(ValueObject):
    """Value Object for an energy load state."""

    current_power: Watts
    timestamp: Timestamp = field(default_factory=Timestamp(datetime.now()))


@dataclass(frozen=True)
class BatteryState(ValueObject):
    """Value Object for a battery state."""

    state_of_charge: Percentage
    remaining_capacity: Optional[WattHours]
    current_power: Watts  # Positive when charging, negative when discharging
    timestamp: Timestamp = field(default_factory=Timestamp(datetime.now()))

    @property
    def charging_power(self) -> Watts:
        """Returns the power being used to charge the battery."""
        return max(self.current_power, Watts(0.0))

    @property
    def discharging_power(self) -> Watts:
        """Returns the power being used to discharge the battery."""
        return max(Watts(-self.current_power), Watts(0.0))


@dataclass(frozen=True)
class GridState(ValueObject):
    """Value Object for a grid state."""

    current_power: Watts  # Positive importing, negative exporting
    timestamp: Timestamp = field(default_factory=Timestamp(datetime.now()))

    @property
    def importing_power(self) -> Watts:
        """Returns the power being imported from the grid."""
        return max(self.current_power, Watts(0.0))

    @property
    def exporting_power(self) -> Watts:
        """Returns the power being exported to the grid."""
        return max(Watts(-self.current_power), Watts(0.0))


@dataclass(frozen=True)
class EnergyStateSnapshot(ValueObject):
    """Value Object for an energy state snapshot."""

    production: Watts
    consumption: LoadState  # Load excluding miner
    battery: Optional[BatteryState]  # Can be None if no battery is present
    grid: Optional[GridState]  # Can be None if no grid is present (e.g., off-grid)
    external_source: Optional[Watts]  # For example, external generator -> future use
    timestamp: Timestamp = field(default_factory=Timestamp(datetime.now()))
