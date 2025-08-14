"""Collection of Value Objects for the Energy System Monitoring domain of the Edge Mining application."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from edge_mining.domain.common import Watts, WattHours, Percentage, Timestamp, ValueObject

@dataclass(frozen=True)
class EnergyReading(ValueObject):
    """Value Object for an energy reading."""
    value: Watts
    timestamp: Timestamp = field(default_factory=datetime.now)

@dataclass(frozen=True)
class BatteryState(ValueObject):
    """Value Object for a battery state."""
    state_of_charge: Percentage
    nominal_capacity: WattHours
    current_power: Watts # Positive when charging, negative when discharging
    timestamp: Timestamp = field(default_factory=datetime.now)

@dataclass(frozen=True)
class EnergyStateSnapshot(ValueObject):
    """Value Object for an energy state snapshot."""
    production: Watts
    consumption: Watts # Load excluding miner
    battery: Optional[BatteryState]
    grid: Optional[Watts] # Positive importing, negative exporting
    #external_source: Optional[Watts] # For example, external generator -> future use
    timestamp: Timestamp = field(default_factory=datetime.now)