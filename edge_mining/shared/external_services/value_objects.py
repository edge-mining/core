"""Collection of Value Objects for the External Service domain of the Edge Mining application."""

from dataclasses import dataclass
from typing import List

from edge_mining.domain.common import ValueObject
from edge_mining.domain.energy.entities import EnergyMonitor
from edge_mining.domain.forecast.entities import ForecastProvider
from edge_mining.domain.home_load.entities import HomeForecastProvider
from edge_mining.domain.miner.entities import MinerController
from edge_mining.domain.notification.entities import Notifier


@dataclass(frozen=True)
class ExternalServiceLinkedEntities(ValueObject):
    """Value Object for entities linked to an External Service"""

    miner_controllers: List[MinerController]
    energy_monitors: List[EnergyMonitor]
    forecast_providers: List[ForecastProvider]
    home_forecast_providers: List[HomeForecastProvider]
    notifiers: List[Notifier]
