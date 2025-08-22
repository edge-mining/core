"""Collection of Entities for the Mining Performace Analysis domain of the Edge Mining application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from edge_mining.domain.common import Entity, Timestamp, EntityId
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.performance.common import (
    MiningPerformanceTrackerAdapter,
    Satoshi,
)
from edge_mining.shared.interfaces.config import MiningPerformanceTrackerConfig


@dataclass
class MiningPerformanceTracker(Entity):
    """Entity for tracking mining performance."""

    name: str = ""
    adapter_type: MiningPerformanceTrackerAdapter = MiningPerformanceTrackerAdapter.DUMMY
    config: Optional[MiningPerformanceTrackerConfig] = None
    external_service_id: Optional[EntityId] = None


@dataclass
class MiningSession(Entity):
    """Entity for a mining session."""

    start_time: Timestamp = field(default_factory=Timestamp(datetime.now()))
    end_time: Optional[Timestamp] = None
    total_reward: Optional[Satoshi] = None
    average_hashrate: Optional[HashRate] = None
    # Add more fields as necessary
    # e.g., total_energy_consumed, efficiency metrics, etc.
