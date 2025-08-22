"""Dummy adapter (Implementation of Port) that simulates a miner control for Edge Mining Application"""

import random
from typing import Optional

from edge_mining.domain.common import Watts
from edge_mining.domain.miner.common import MinerStatus
from edge_mining.domain.miner.ports import MinerControlPort
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.logging.port import LoggerPort


class DummyMinerController(MinerControlPort):
    """Simulates miner control without real hardware."""

    def __init__(
        self,
        initial_status: MinerStatus = MinerStatus.UNKNOWN,
        power_max: Optional[Watts] = None,
        hashrate_max: Optional[HashRate] = None,
        logger: Optional[LoggerPort] = None,
    ):
        self._status = initial_status
        self._power_max = power_max or Watts(3200.0)
        self._hashrate_max = hashrate_max or HashRate(90, "TH/s")
        self.logger = logger

        self._power: Watts = Watts(0.0)

    def start_miner(self) -> bool:
        """Start the miner."""
        print(f"DummyController: Received START (current: {self._status.name})")
        if self._status != MinerStatus.ON:
            self._status = MinerStatus.STARTING
            # Simulate startup time
            # In a real scenario, this would just send the command
            # The status check next cycle would confirm if it's ON
            if self.logger:
                self.logger.debug("DummyController: Setting status to STARTING")
            # Simulate transition after a delay for testing purposes if needed
            # threading.Timer(5, self._set_status, args=(MinerStatus.ON)).start()
        return True  # Assume command sent successfully

    def stop_miner(self) -> bool:
        """Stop the miner."""
        if self.logger:
            self.logger.debug(f"DummyController: Received STOP (current: {self._status.name})")
        if self._status == MinerStatus.ON:
            self._status = MinerStatus.STOPPING
            if self.logger:
                self.logger.debug("DummyController: Setting status to STOPPING")
            # Simulate transition
            # threading.Timer(3, self._set_status, args=(MinerStatus.OFF).start()
        return True  # Assume command sent successfully

    def get_miner_status(self) -> MinerStatus:
        """Get the status of the miner."""
        # Simulate state transitions finishing for dummy purposes
        if self._status == MinerStatus.STARTING:
            if random.random() < 0.8:  # 80% chance it finished starting
                if self.logger:
                    self.logger.debug("DummyController: Simulating finished starting -> ON")
                self._status = MinerStatus.ON
            else:
                if self.logger:
                    self.logger.debug("DummyController: Simulating still STARTING")

        elif self._status == MinerStatus.STOPPING:
            if random.random() < 0.9:  # 90% chance it finished stopping
                if self.logger:
                    self.logger.debug("DummyController: Simulating finished stopping -> OFF")
                self._status = MinerStatus.OFF
            else:
                if self.logger:
                    self.logger.debug("DummyController: Simulating still STOPPING")

        status = self._status
        if self.logger:
            self.logger.debug(f"DummyController: Reporting status {status.name}")
        return status

    def get_miner_power(self) -> Optional[Watts]:
        """Get the power of the miner."""
        status = self._status
        if status == MinerStatus.ON:
            power = Watts(random.uniform(500, self._power_max))
            if self.logger:
                self.logger.debug(f"DummyController: Reporting power {power:.0f}W")
        elif status == MinerStatus.STARTING:
            power = Watts(random.uniform(10, 200))  # Lower power during startup
            if self.logger:
                self.logger.debug(f"DummyController: Reporting power {power:.0f}W")
        else:
            if self.logger:
                self.logger.debug(f"DummyController: Reporting power 0W (status: {status.name})")
            power = Watts(0.0)

        self._power = power
        return power

    def get_miner_hashrate(self) -> Optional[HashRate]:
        """Get the hash rate of the miner."""
        status = self._status
        if status == MinerStatus.ON:
            # Simulate hash rate
            hash_rate = HashRate(
                value=random.uniform(0, self._hashrate_max.value),
                unit=self._hashrate_max.unit,
            )
            if self.logger:
                self.logger.debug(f"DummyController: Reporting hash rate {hash_rate.value:.2f} {hash_rate.unit}")
            return hash_rate
        else:
            if self.logger:
                self.logger.debug(f"DummyController: Reporting hash rate 0 (status: {status.name})")
            return HashRate(value=0.0, unit="TH/s")

    # Helper for simulated transitions (if using timers)
    # def _set_status(self, status: MinerStatus):
    #      print(f"DummyController: Timer finished, setting to {status.name}")
    #      self._status = status
