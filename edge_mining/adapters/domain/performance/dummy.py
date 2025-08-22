"""
Dummy adapter (Implementation of Port) that simulates
a miner performance tracker for Edge Mining Application
"""

import random
from typing import List, Optional

from edge_mining.domain.common import EntityId
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.performance.ports import (
    MiningPerformanceTrackerPort,
    MiningReward,
)


class DummyMiningPerformanceTracker(MiningPerformanceTrackerPort):
    """Dummy implementation of the MiningPerformanceTrackerPort."""

    def get_current_hashrate(self, miner_ids: List[EntityId]) -> Optional[HashRate]:
        # Requires miner status knowledge - should ideally integrate with controller
        # or miner repo or query pool API
        print(f"DummyMiningPerformanceTracker: Getting hashrate for {miner_ids} (Not Implemented Yet)")
        # Simulate based on a known power? Needs more info.

        return HashRate(value=random.uniform(90.0, 110.0), unit="TH/s")

    def get_recent_rewards(self, miner_id: Optional[EntityId] = None, limit: int = 10) -> List[MiningReward]:
        print(f"DummyPerformanceTracker: Getting rewards for {miner_id} (Not Implemented Yet)")
        # Would query pool API
        return []
