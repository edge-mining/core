"""Collection of Aggregate Roots for the Home Consumption Analytics domain of the Edge Mining application."""

from dataclasses import dataclass, field
from typing import Dict
import uuid

from edge_mining.domain.common import EntityId
from edge_mining.domain.home_load.entities import LoadDevice

@dataclass
class HomeLoadsProfile:
    """Aggregate Root for the Home Loads."""
    id: EntityId = field(default_factory=uuid.uuid4)
    name: str = "Default Home Profile"
    devices: Dict[EntityId, LoadDevice] = field(default_factory=dict)
    # We might store aggregated historical data or patterns here
    # For simplicity now, the forecasting logic is external (in the adapter)
