"""Collection of Value Objects for the Mining Performace Analysis domain of the Edge Mining application."""

from dataclasses import dataclass, field
from datetime import datetime

from edge_mining.domain.common import Timestamp, ValueObject
from edge_mining.domain.performance.common import Satoshi


@dataclass(frozen=True)
class MiningReward(ValueObject):
    """Value Object for a mining reward."""

    amount: Satoshi
    timestamp: Timestamp = field(default_factory=Timestamp(datetime.now()))
