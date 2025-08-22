"""Collection of Entities for the Home Consumption Analytics domain of the Edge Mining application."""

from dataclasses import dataclass
from typing import Optional

from edge_mining.domain.common import Entity, EntityId
from edge_mining.domain.home_load.common import HomeForecastProviderAdapter
from edge_mining.shared.interfaces.config import HomeForecastProviderConfig


@dataclass
class LoadDevice(Entity):
    """Entity for a load device."""

    name: str = ""  # e.g., "Dishwasher", "EV Charger"
    type: str = ""  # e.g., "Appliance", "Heating"
    # Could store typical consumption patterns here but I'll think about it later


@dataclass
class HomeForecastProvider(Entity):
    """Entity for a home forecast provider."""

    name: str = ""
    adapter_type: HomeForecastProviderAdapter = HomeForecastProviderAdapter.DUMMY
    config: Optional[HomeForecastProviderConfig] = None
    external_service_id: Optional[EntityId] = None
