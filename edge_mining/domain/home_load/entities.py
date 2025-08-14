"""Collection of Entities for the Home Consumption Analytics domain of the Edge Mining application."""

from dataclasses import dataclass, field
import uuid

from edge_mining.domain.common import EntityId

@dataclass
class LoadDevice:
    """Entity for a load device."""
    id: EntityId = field(default_factory=uuid.uuid4)
    name: str = "" # e.g., "Dishwasher", "EV Charger"
    type: str = "" # e.g., "Appliance", "Heating"
    # Could store typical consumption patterns here 📈​📉 but I'll think about it later