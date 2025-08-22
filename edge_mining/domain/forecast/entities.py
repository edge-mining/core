"""Collection of Entities for the Forcast domain of the Edge Mining application."""

from dataclasses import dataclass
from typing import Optional

from edge_mining.domain.common import Entity, EntityId
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.shared.interfaces.config import ForecastProviderConfig


@dataclass
class ForecastProvider(Entity):
    """Entity for a forecast provider."""

    name: str = ""
    adapter_type: ForecastProviderAdapter = ForecastProviderAdapter.DUMMY_SOLAR
    config: Optional[ForecastProviderConfig] = None
    external_service_id: Optional[EntityId] = None
