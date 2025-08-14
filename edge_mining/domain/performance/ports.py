"""Collection of Ports for the Mining Performace Analysis domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import Optional, List

from edge_mining.domain.miner.common import MinerId 
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.performance.values_objects import MiningReward

class MiningPerformanceTrackerPort(ABC):
    """Port for the Mining Performance Tracker."""
    @abstractmethod
    def get_current_hashrate(self, miner_id: MinerId) -> Optional[HashRate]:
        """Gets the current hashrate from the pool or device."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_rewards(self, miner_id: Optional[MinerId] = None, limit: int = 10) -> List[MiningReward]:
        """Gets recent mining rewards."""
        raise NotImplementedError
