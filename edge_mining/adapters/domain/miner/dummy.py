"""Dummy adapter (Implementation of Port) that simulates a miner control for Edge Mining Application"""

from typing import Optional, Dict
import random

from edge_mining.domain.common import Watts
from edge_mining.domain.miner.ports import MinerControlPort
from edge_mining.domain.miner.common import MinerId, MinerStatus
from edge_mining.domain.miner.value_objects import HashRate

class DummyMinerController(MinerControlPort):
    """Simulates miner control without real hardware."""
    def __init__(
        self,
        initial_status: Optional[Dict[MinerId, MinerStatus]] = None,
        power_w: float = 1500.0
    ):
        self._status: Dict[MinerId, MinerStatus] = initial_status if initial_status else {}
        self._power = Watts(power_w)

    def _ensure_miner(self, miner_id: MinerId):
        """Ensure the miner is in the status dictionary."""
        if miner_id not in self._status:
            self._status[miner_id] = MinerStatus.UNKNOWN # Default if never seen

    def start_miner(self, miner_id: MinerId) -> bool:
        """Start the miner."""
        self._ensure_miner(miner_id)
        print(f"DummyController: Received START for {miner_id} (current: {self._status[miner_id].name})")
        if self._status[miner_id] != MinerStatus.ON:
            self._status[miner_id] = MinerStatus.STARTING
            # Simulate startup time
            # In a real scenario, this would just send the command
            # The status check next cycle would confirm if it's ON
            print(f"DummyController: Setting {miner_id} status to STARTING")
            # Simulate transition after a delay for testing purposes if needed
            # threading.Timer(5, self._set_status, args=(miner_id, MinerStatus.ON)).start()
        return True # Assume command sent successfully

    def stop_miner(self, miner_id: MinerId) -> bool:
        """Stop the miner."""
        self._ensure_miner(miner_id)
        print(f"DummyController: Received STOP for {miner_id} (current: {self._status[miner_id].name})")
        if self._status[miner_id] == MinerStatus.ON:
            self._status[miner_id] = MinerStatus.STOPPING
            print(f"DummyController: Setting {miner_id} status to STOPPING")
            # Simulate transition
            # threading.Timer(3, self._set_status, args=(miner_id, MinerStatus.OFF)).start()
        return True # Assume command sent successfully

    def get_miner_status(self, miner_id: MinerId) -> MinerStatus:
        """Get the status of the miner."""
        self._ensure_miner(miner_id)
        # Simulate state transitions finishing for dummy purposes
        if self._status[miner_id] == MinerStatus.STARTING:
            if random.random() < 0.8: # 80% chance it finished starting
                print(f"DummyController: Simulating {miner_id} finished starting -> ON")
                self._status[miner_id] = MinerStatus.ON
            else:
                print(f"DummyController: Simulating {miner_id} still STARTING")

        elif self._status[miner_id] == MinerStatus.STOPPING:
            if random.random() < 0.9: # 90% chance it finished stopping
               print(f"DummyController: Simulating {miner_id} finished stopping -> OFF")
               self._status[miner_id] = MinerStatus.OFF
            else:
               print(f"DummyController: Simulating {miner_id} still STOPPING")

        status = self._status.get(miner_id, MinerStatus.UNKNOWN)
        print(f"DummyController: Reporting status {status.name} for {miner_id}")
        return status

    def get_miner_power(self, miner_id: MinerId) -> Optional[Watts]:
        """Get the power of the miner."""
        self._ensure_miner(miner_id)
        status = self._status.get(miner_id)
        if status == MinerStatus.ON:
            power = Watts(self._power + random.uniform(-50, 50)) # Add some noise
            print(f"DummyController: Reporting power {power:.0f}W for {miner_id}")
            return power
        elif status == MinerStatus.STARTING:
            power = Watts(self._power * random.uniform(0.3, 0.7)) # Lower power during startup
            print(f"DummyController: Reporting power {power:.0f}W for {miner_id}")
            return power
        else:
            print(f"DummyController: Reporting power 0W for {miner_id} (status: {status.name})")
            return Watts(0.0)

    def get_miner_hashrate(self, miner_id: MinerId) -> Optional[HashRate]:
        """Get the hash rate of the miner."""
        self._ensure_miner(miner_id)
        status = self._status.get(miner_id)
        if status == MinerStatus.ON:
            # Simulate hash rate
            hash_rate = HashRate(value=random.uniform(20, 100), unit="TH/s")
            print(f"DummyController: Reporting hash rate {hash_rate.value:.2f} {hash_rate.unit} for {miner_id}")
            return hash_rate
        else:
            print(f"DummyController: Reporting hash rate 0 for {miner_id} (status: {status.name})")
            return HashRate(value=0.0, unit="TH/s")

    # Helper for simulated transitions (if using timers)
    # def _set_status(self, miner_id: MinerId, status: MinerStatus):
    #      print(f"DummyController: Timer finished, setting {miner_id} to {status.name}")
    #      self._status[miner_id] = status
