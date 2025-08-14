"""Dummy adapter (Implementation of Port) that simulates a miner performance tracker for Edge Mining Application"""

from typing import Optional, List
import random

from edge_mining.domain.performance.ports import MiningPerformanceTrackerPort, MiningReward
from edge_mining.domain.miner.common import MinerId
from edge_mining.domain.miner.value_objects import HashRate

class DummyPerformanceTracker(MiningPerformanceTrackerPort):
    """Dummy implementation of the MiningPerformanceTrackerPort."""
    def get_current_hashrate(self, miner_id: MinerId) -> Optional[HashRate]:
        # Requires miner status knowledge - should ideally integrate with controller or miner repo
        # Or query pool API
        print(f"DummyPerformanceTracker: Getting hashrate for {miner_id} (Not Implemented Yet)")
        # Simulate based on a known power? Needs more info.
        # Example if we knew miner 'dummy01' was ON:
        if miner_id == "dummy01":
            return HashRate(value=random.uniform(90.0, 110.0), unit="TH/s")
        return None

    def get_recent_rewards(self, miner_id: Optional[MinerId] = None, limit: int = 10) -> List[MiningReward]:
        print(f"DummyPerformanceTracker: Getting rewards for {miner_id} (Not Implemented Yet)")
        # Would query pool API
        return []
