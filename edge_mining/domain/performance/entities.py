"""Collection of Entities for the Mining Performace Analysis domain of the Edge Mining application."""

from dataclasses import dataclass, field
from typing import Optional
import uuid

from edge_mining.domain.common import EntityId
from edge_mining.domain.common import Timestamp
from edge_mining.domain.miner.common import MinerId
from edge_mining.domain.performance.common import Satoshi
from edge_mining.domain.miner.value_objects import HashRate

@dataclass
class MiningSession:
    """Entity for a mining session."""
    id: EntityId = field(default_factory=uuid.uuid4)
    miner_id: MinerId
    start_time: Timestamp
    end_time: Optional[Timestamp] = None
    total_reward: Optional[Satoshi] = None
    average_hashrate: Optional[HashRate] = None
    # Add more fields as necessary
    # e.g., total_energy_consumed, efficiency metrics, etc.
